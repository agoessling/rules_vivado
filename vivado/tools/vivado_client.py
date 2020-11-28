#!/usr/bin/env python3

import argparse
import functools
import os
import os.path
import re
import socket
import sys


def make_green(b):
  return b'\033[0;32m' + b + b'\033[0m'

def make_yellow(b):
  return b'\033[0;33m' + b + b'\033[0m'

def make_red(b):
  return b'\033[0;31m' + b + b'\033[0m'


class CommandFailure(Exception):
  pass


class CommandTimeout(Exception):
  pass


class VivadoClient:
  PROMPT = b'Vivado% '

  WHITE_LIST = [
      b'Common 17-53',  # Error regarding closing non-existent project.
      b'Place 46-29',  # Warning about skipping physical synthesis in placer.
      b'Synth 8-1921',  # Incorrect warning about system task syntax.
  ]

  def _command(timeout=None):
    '''This setup allows default arguments.'''
    def _decorate(function):
      @functools.wraps(function)
      def wrapped_function(self, *args, **kwargs):
        function(self, *args, **kwargs)
        return self._get_response(timeout=timeout)

      return wrapped_function
    return _decorate

  def __init__(self, host, port, verbose):
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.settimeout(0.2)
    self.socket.connect((host, port))

    self.buffer = bytearray()
    self.verbose = verbose

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, exc_traceback):
    self.close()

  def close(self):
    self.socket.close()

  def _reset_buffer(self):
    self.buffer = bytearray()

  def _get_line(self):
    while True:
      if self.buffer == self.PROMPT:
        self._reset_buffer()
        return bytes(self.PROMPT)

      line, sep, remaining = self.buffer.partition(b'\n')

      if sep:
        self.buffer = remaining
        return bytes(line + sep)

      try:
        self.buffer += self.socket.recv(1024)
      except socket.timeout:
        return b''

  def _handle_line(self, line):
    line_type = 'COMMON'

    match = re.match(b'(.+?): \[(.+?)\]', line)
    if match:
      if match.group(2) in self.WHITE_LIST:
        line_type = 'INFO'
      elif match.group(1) in (b'INFO', b'WARNING', b'CRITICAL WARNING', b'ERROR'):
        line_type = match.group(1).decode()
      else:
        line_type = 'INFO'

    is_error = line_type in ('WARNING', 'CRITICAL WARNING', 'ERROR')

    color_func = {
        'COMMON': lambda x: x,
        'INFO': make_green,
        'WARNING': make_yellow,
        'CRITICAL WARNING': make_red,
        'ERROR': make_red
    }

    if self.verbose or is_error:
      os.write(sys.stdout.fileno(), color_func[line_type](line))

    return not is_error

  def _get_response(self, timeout=None):
    self.socket.settimeout(timeout)

    resp = bytearray()
    success = True
    while True:
      line = self._get_line()

      # Timeout.
      if not line:
        raise CommandTimeout()

      if not self._handle_line(line):
        success = False

      # Command has completed.
      if line == self.PROMPT:
        if not success:
          raise CommandFailure()
        return resp.decode()

      resp += line

  @_command()
  def change_directory(self, path):
    self.socket.sendall('cd {:s}\r'.format(path).encode())

  @_command()
  def set_part(self, part):
    self.socket.sendall('set_part {:s}\r'.format(part).encode())

  @_command()
  def read_xdc(self, constraints):
    cmd = 'read_xdc {{{:s}}}\r'.format(' '.join(constraints))
    self.socket.sendall(cmd.encode())

  @_command()
  def read_verilog(self, files, system_verilog=False):
    sv_flag = ' -sv' if system_verilog else ''
    cmd = 'read_verilog{:s} {{{:s}}}\r'.format(sv_flag, ' '.join(files))
    self.socket.sendall(cmd.encode())

  @_command()
  def synth_design(self, top, part):
    self.socket.sendall('synth_design -top {:s} -part {:s}\r'.format(top, part).encode())

  @_command()
  def close_project(self):
    self.socket.sendall(b'close_project\r')

  @_command()
  def write_checkpoint(self, filename):
    self.socket.sendall('write_checkpoint -force {:s}\r'.format(filename).encode())

  @_command()
  def read_checkpoint(self, filename):
    self.socket.sendall('read_checkpoint {:s}\r'.format(filename).encode())

  @_command()
  def link_design(self):
    self.socket.sendall(b'link_design\r')

  @_command()
  def opt_design(self):
    self.socket.sendall(b'opt_design\r')

  @_command()
  def place_design(self):
    self.socket.sendall(b'place_design -no_timing_driven\r')

  @_command()
  def phys_opt_design(self):
    self.socket.sendall(b'phys_opt_design\r')

  @_command()
  def route_design(self):
    self.socket.sendall(b'route_design\r')

  @_command()
  def write_bitstream(self, filename):
    self.socket.sendall('write_bitstream -force {:s}\r'.format(filename).encode())

  @_command()
  def open_hw_manager(self):
    self.socket.sendall(b'open_hw_manager\r')

  @_command()
  def close_hw_manager(self):
    self.socket.sendall(b'close_hw_manager\r')

  @_command()
  def connect_hw_server(self):
    self.socket.sendall(b'connect_hw_server\r')

  @_command()
  def open_hw_target(self):
    self.socket.sendall(b'open_hw_target\r')

  @_command()
  def set_property(self, prop_dict, objects):
    dict_string = ' '.join(['{} {}'.format(key, val) for key, val in prop_dict.items()])
    cmd = 'set_property -dict {{{:s}}} [{:s}]\r'.format(dict_string, objects)
    self.socket.sendall(cmd.encode())

  @_command()
  def program_hw_devices(self):
    self.socket.sendall(b'program_hw_devices [current_hw_device]\r')

  @_command()
  def write_cfgmem(self, input_file, output_file, size, interface):
    cmd_args = [
        'write_cfgmem',
        '-format bin',
        '-size {:d}'.format(size),
        '-interface {:s}'.format(interface),
        '-loadbit {{up 0x00000000 {:s}}}'.format(input_file),
        '-force',
        '-file {:s}\r'.format(output_file),
    ]
    self.socket.sendall(' '.join(cmd_args).encode())

  @_command()
  def create_hw_cfgmem(self, memory):
    cmd = 'create_hw_cfgmem -hw_device [current_hw_device] {:s}\r'.format(memory)
    self.socket.sendall(cmd.encode())

  @_command()
  def program_hw_cfgmem(self):
    self.socket.sendall(b'program_hw_cfgmem [current_hw_cfgmem]\r')

  @_command()
  def create_hw_bitstream(self, filename):
    cmd = 'create_hw_bitstream -hw_device [current_hw_device] {:s}\r'.format(filename)
    self.socket.sendall(cmd.encode())

  @_command()
  def boot_hw_device(self):
    self.socket.sendall(b'boot_hw_device [current_hw_device]\r')

  @_command()
  def _check_timing(self):
    self.socket.sendall(b'check_timing\r')

  def check_timing(self):
    resp = self._check_timing()

    header = r'^\d+\..+\r\n-+\r\n'
    pattern = r'{}[\s\S]+?(?=(?:{})|\Z)'.format(header, header)

    checks = re.findall(pattern, resp, flags=re.MULTILINE)

    if not checks:
      raise RuntimeError('Could not parse check_timing response.')

    errors = []
    for check in checks:
      match = re.match(r'\d+\..+\((\d+)\)\r\n', check)

      if not match:
        raise RuntimeError('Could not parse check_timing response.')

      if int(match.group(1)) != 0:
        errors.append(check)

    if errors:
      os.write(sys.stdout.fileno(), make_red(b'\nCheck timing produced errors:\n\n'))

      for error in errors:
        os.write(sys.stdout.fileno(), make_red(error.encode()))

    return len(errors) == 0

  @_command()
  def _report_drc(self):
    self.socket.sendall(b'report_drc -no_waivers -upgrade_cw '
        b'-ruledecks {default opt_checks placer_checks router_checks '
        b'bitstream_checks incr_eco_checks eco_checks abs_checks}\r')

  def _handle_report(self, response, name):
    header = r'^\d+\..+\r\n-+\r\n'
    pattern = r'{}[\s\S]+?(?=(?:{})|^.+completed successfully)'.format(header, header)

    sections = re.findall(pattern, response, flags=re.MULTILINE)
    if len(sections) != 2:
      raise RuntimeError('Could not parse Report {:s} response.'.format(name))

    match = re.search(r'Violations found: (\d+)\s*$', response, flags=re.MULTILINE)
    if not match:
      raise RuntimeError('Could not parse Report {:s} response.'.format(name))
    errors = int(match.group(1))

    if errors:
      os.write(sys.stdout.fileno(),
          make_red('\nReport {:s} produced {:d} errors:\n\n'.format(name, errors).encode()))
      os.write(sys.stdout.fileno(), make_red(sections[1].encode()))
      os.write(sys.stdout.fileno(), make_red(sections[0].encode()))

    return errors == 0

  def report_drc(self):
    resp = self._report_drc()
    return self._handle_report(resp, 'DRC')

  @_command()
  def _report_methodology(self):
    self.socket.sendall(b'report_methodology -no_waivers -checks [get_methodology_checks]\r')

  def report_methodology(self):
    resp = self._report_methodology()
    return self._handle_report(resp, 'Methodology')

  @_command()
  def _report_timing(self):
    self.socket.sendall(b'report_timing -delay_type min_max -max_paths 1 -slack_less_than 0\r')

  def report_timing(self):
    resp = self._report_timing()

    sections = re.split(r'^Timing Report\r\n', resp, flags=re.MULTILINE)

    if len(sections) != 2:
      raise RuntimeError('Could not parse Report {:s} response.'.format(name))

    match = re.search(r'No timing paths found.', sections[1])
    if not match:
      os.write(sys.stdout.fileno(), make_red(b'\nReport timing produced errors:\n\n'))
      os.write(sys.stdout.fileno(), make_red(sections[1].encode()))
      return False

    return True


def preamble(client, args):
  client.close_project()
  client.set_part(args.part)

  if args.constraint:
    client.read_xdc(args.constraint)


def synthesize(client, args):
  preamble(client, args)

  # Check extensions for system verilog.
  sv = False
  if any([f.endswith('.sv') for f in args.verilog]):
    sv = True

  client.read_verilog(args.verilog, sv)
  client.synth_design(args.top, args.part)

  client.write_checkpoint(args.output)


def place(client, args):
  preamble(client, args)

  client.read_checkpoint(args.input)
  client.link_design()
  client.opt_design()
  client.place_design()
  client.phys_opt_design()

  client.write_checkpoint(args.output)


def route(client, args):
  preamble(client, args)

  client.read_checkpoint(args.input)
  client.link_design()
  client.route_design()

  client.write_checkpoint(args.output)


def bitstream(client, args):
  preamble(client, args)

  client.read_checkpoint(args.input)
  client.link_design()

  client.write_bitstream(args.output)

  if args.check:
    if not _check(client):
      raise CommandFailure()


def load(client, args):
  preamble(client, args)

  client.open_hw_manager()
  client.connect_hw_server()
  client.open_hw_target()
  client.set_property({'PROGRAM.FILE': args.input}, 'current_hw_device')
  client.program_hw_devices()
  client.close_hw_manager()


def cfg_mem(client, args):
  preamble(client, args)
  client.write_cfgmem(
      input_file=args.input,
      output_file=args.output,
      size=args.size,
      interface=args.interface
  )


def flash(client, args):
  preamble(client, args)

  client.open_hw_manager()
  client.connect_hw_server()
  client.open_hw_target()
  client.create_hw_cfgmem(args.memory)

  props = {
      'PROGRAM.FILES': args.input,
      'PROGRAM.ADDRESS_RANGE': 'use_file',
      'PROGRAM.ERASE': 1,
      'PROGRAM.BLANK_CHECK': 0,
      'PROGRAM.CFG_PROGRAM': 1,
      'PROGRAM.VERIFY': 1,
      'PROGRAM.CHECKSUM': 0,
  }
  client.set_property(props, 'current_hw_cfgmem')

  # Load Xilinx provided bitstream to facilitate flashing of configuration memory.
  client.create_hw_bitstream('[get_property PROGRAM.HW_CFGMEM_BITFILE [current_hw_device]]')
  client.program_hw_devices()

  client.program_hw_cfgmem()
  client.boot_hw_device()

  client.close_hw_manager()


def _check(client):
  success = True
  success &= client.check_timing()
  success &= client.report_drc()
  success &= client.report_methodology()
  success &= client.report_timing()

  return success


def check(client, args):
  preamble(client, args)

  client.read_checkpoint(args.input)
  client.link_design()

  if not _check(client):
    raise CommandFailure()


def main():
  parser = argparse.ArgumentParser(description='Client for interacting with Vivado.')
  subparsers = parser.add_subparsers(help='Command to perform.', dest='command')
  subparsers.required = True

  # Common Arguments.
  parser_parent = argparse.ArgumentParser(add_help=False)
  parser_parent.add_argument('-p', '--part', required=True, help='Part number.')
  parser_parent.add_argument('-c', '--constraint', nargs='+', help='Constraint file.')
  parser_parent.add_argument('--verbose', action='store_true',
                             help='Display all output, not just errors.')
  parser_parent.add_argument('--host', default='localhost', help='A hostname to which to connect.')
  parser_parent.add_argument('--port', type=int, default=9191, help='A port number for connection.')

  # Output Argument.
  parser_output = argparse.ArgumentParser(add_help=False)
  parser_output.add_argument('-o', '--output', required=True, help='Output file.')

  # Input Argument.
  parser_input = argparse.ArgumentParser(add_help=False)
  parser_input.add_argument('-i', '--input', required=True, help='Input file.')

  # Synth Command.
  parser_synth = subparsers.add_parser('synth', parents=[parser_parent, parser_output],
                                       help='Synthesize design.')
  parser_synth.add_argument('-v', '--verilog', nargs='+', required=True, help='Verilog file.')
  parser_synth.add_argument('-t', '--top', required=True, help='Top level module name.')
  parser_synth.set_defaults(func=synthesize)

  # Place Command.
  parser_place = subparsers.add_parser('place',
                                       parents=[parser_parent, parser_input, parser_output],
                                       help='Place design.')
  parser_place.set_defaults(func=place)

  # Route Command.
  parser_route = subparsers.add_parser('route',
                                       parents=[parser_parent, parser_input, parser_output],
                                       help='Route design.')
  parser_route.set_defaults(func=route)

  # Bitstream Command.
  parser_bitstream = subparsers.add_parser('bitstream',
                                           parents=[parser_parent, parser_input, parser_output],
                                           help='Write bitstream.')
  parser_bitstream.add_argument('--check', action='store_true', help='Perform check on design.')
  parser_bitstream.set_defaults(func=bitstream)

  # Configuration Memory Command.
  valid_interfaces = [
      'SMAPx8', 'SMAPx16', 'SMAPx32', 'SERIALx1',
      'SPIx1', 'SPIx2', 'SPIx4', 'SPIx8', 'BPIx8', 'BPIx16'
  ]
  parser_cfg_mem = subparsers.add_parser('cfg_mem',
                                         parents=[parser_parent, parser_input, parser_output],
                                         help='Write config memory file.')
  parser_cfg_mem.add_argument('--size', type=int, required=True, help='Memory size [MB].')
  parser_cfg_mem.add_argument('--interface', choices=valid_interfaces, required=True,
                              help='Memory size [MB].')
  parser_cfg_mem.set_defaults(func=cfg_mem)

  # Load Command.
  parser_load = subparsers.add_parser('load',
                                      parents=[parser_parent, parser_input],
                                      help='Load bitstream.')
  parser_load.set_defaults(func=load)

  # Flash Command.
  parser_flash = subparsers.add_parser('flash',
                                       parents=[parser_parent, parser_input],
                                       help='Flash bitstream to configuration memory.')
  parser_flash.add_argument('--memory', required=True, help='Vivado memory part number.')
  parser_flash.set_defaults(func=flash)

  # Check Command.
  parser_check = subparsers.add_parser('check',
                                       parents=[parser_parent, parser_input],
                                       help='Run design checks.')
  parser_check.set_defaults(func=check)

  # Execute command.
  args = parser.parse_args()

  with VivadoClient(args.host, args.port, args.verbose) as client:
    try:
      client.change_directory(os.getcwd())
      args.func(client, args)
    except (CommandTimeout, CommandFailure):
      try:
        os.remove(args.output)
      except (OSError, AttributeError):
        pass
      os.write(sys.stdout.fileno(), make_red(b'\nCommand Failed.\n'))
      sys.exit(1)

  # Give a final return character.
  if args.verbose:
    os.write(sys.stdout.fileno(), b'\n')


if __name__ == '__main__':
  main()
