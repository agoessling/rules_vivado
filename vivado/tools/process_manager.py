import atexit
import os
import psutil
import select
import socket
import subprocess
import sys
import termios
import threading
import tty


class ProcessServer:
  def __init__(self, monitor, host='localhost', port=9191):
    self.monitor = monitor
    self.host = host
    self.port = port

    self.should_run_event = threading.Event()

  def _should_run(self):
    # Make sure monitor is still healthy and exit if not.
    if not self.monitor.is_alive():
      self.monitor.stop()
      print('\r\nPROCESS SERVER: Monitor exited.\r\n', end='')
      return False

    return self.should_run_event.is_set()

  def _server_thread(self):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
      # Setup non-blocking, reusing port, with only one allowed pending connection.
      s.settimeout(0.2)
      s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      s.bind((self.host, self.port))
      s.listen(1)

      while self._should_run():
        try:
          conn, addr = s.accept()
        except socket.timeout:
          continue

        with conn:
          print('\r\nPROCESS SERVER: Connected to {}.\r\n'.format(addr), end='')
          conn.settimeout(0.2)

          # Discard data from before connection.
          self.monitor.read()

          # Continually interact with connection.
          while self._should_run():
            connection_closed = False

            try:
              rx_data = conn.recv(1024)
              if not rx_data:  # Empty receive indicates closed connection.
                connection_closed = True
            except socket.timeout:
              rx_data = b''
            except OSError:
              rx_data = b''
              connection_closed = True

            if rx_data:
              self.monitor.write(rx_data)

            tx_data = self.monitor.read()
            if tx_data:
              try:
                conn.sendall(tx_data)
              except OSError:
                connection_closed = True

            if connection_closed:
              print('\r\nPROCESS SERVER: Connection closed.\r\n', end='')
              break


  def _stop_server_thread(self):
    self.should_run_event.clear()
    self.server_thread.join(1.0)
    if self.server_thread.is_alive():
      raise Exception('Could not stop thread.')

  def run(self):
    self.monitor.run()

    self.should_run_event.set()
    self.server_thread = threading.Thread(target=self._server_thread, daemon=True)
    self.server_thread.start()

  def stop(self):
    self.monitor.stop()
    self._stop_server_thread()

  def serve_forever(self):
    self.run()
    self.server_thread.join()

  def is_alive(self):
    return self.server_thread.is_alive()


class ProcessMonitor:
  def __init__(self, args, tee_stdin=False, tee_stdout=False, raw_mode=False):
    self.args = args
    self.tee_stdin = tee_stdin
    self.tee_stdout = tee_stdout
    self.raw_mode = raw_mode

    self.should_run = threading.Event()

    self.buffer_lock = threading.Lock()
    self.buffer_ready = threading.Event()
    self.buffer = bytearray()

    self.process = None
    self.polling_thread = None

    # Save terminal settings to revert to if necessary.
    self.termios_settings = termios.tcgetattr(sys.stdin.fileno())

  def _enter_raw_mode(self):
    tty.setraw(sys.stdin.fileno())

  def _exit_raw_mode(self):
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self.termios_settings)

  def _polling_thread(self):
    read_list = [self.out_r]
    if self.tee_stdin:
      read_list.append(sys.stdin.fileno())

    while self.should_run.is_set():
      ready_list, _, _ = select.select(read_list, [], [], 0.2)
      # Continue on timeout.
      if not ready_list:
        continue

      stdin_bytes = b''
      stdout_bytes = b''

      for fd in ready_list:
        if fd == sys.stdin.fileno():
          stdin_bytes = os.read(sys.stdin.fileno(), 1024)
        if fd == self.out_r:
          stdout_bytes = os.read(self.out_r, 1024)

      if stdin_bytes and self.tee_stdin:
        os.write(self.in_w, stdin_bytes)

      if stdout_bytes and self.tee_stdout:
        os.write(sys.stdout.fileno(), stdout_bytes)

      if stdout_bytes:
        with self.buffer_lock:
          self.buffer.extend(stdout_bytes)
          self.buffer_ready.set()

  def _stop_polling_thread(self):
    self.should_run.clear()

    # Only stop it if it exists.
    if not self.polling_thread:
      return

    self.polling_thread.join(1.0)
    if self.polling_thread.is_alive():
      raise Exception('Could not stop thread.')

  def read(self):
    with self.buffer_lock:
      buffer_bytes = bytes(self.buffer)
      self.buffer = bytearray()
      self.buffer_ready.clear()
      return buffer_bytes

  def read_line(self):
    with self.buffer_lock:
      line, sep, remainder = self.buffer.partition(b'\n')

      if not sep:
        return b''

      self.buffer = remainder
      if not self.buffer:
        self.buffer_ready.clear()

      return bytes(line + sep)

  def write(self, data):
    os.write(self.in_w, data)
    if self.tee_stdout and not self.raw_mode:
      os.write(sys.stdout.fileno(), data)

  def run(self):
    # Ensure the process and thread are always cleaned up.
    atexit.register(self.stop)

    if self.tee_stdin and self.raw_mode:
      self._enter_raw_mode()

    self.in_r, self.in_w = os.openpty()
    self.out_r, self.out_w = os.openpty()

    self.process = subprocess.Popen(self.args,
                                    stdin=self.in_r,
                                    stdout=self.out_w,
                                    stderr=subprocess.STDOUT)

    self.should_run.set()
    self.polling_thread = threading.Thread(target=self._polling_thread, daemon=True)
    self.polling_thread.start()

  def _terminate_processes(self):
    # Only proceed if process is still running.
    if not self.process or self.process.poll() is not None:
      return

    parent = psutil.Process(self.process.pid)
    children = parent.children(recursive=True)
    procs = children + [parent]

    for p in procs:
      p.terminate()

    gone, alive = psutil.wait_procs(procs, timeout=1)

    for p in alive:
      p.kill()

  def is_alive(self):
    return self.process.poll() is None and self.polling_thread.is_alive()

  def stop(self):
    self._terminate_processes()
    self._stop_polling_thread()
    self._exit_raw_mode()
