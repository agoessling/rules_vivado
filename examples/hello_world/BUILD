load("@rules_verilog//verilog:defs.bzl", "verilog_module")

load(
    "@rules_vivado//vivado:defs.bzl",
    "vivado_project",
    "vivado_bitstream",
    "vivado_config_memory",
    "vivado_load",
    "vivado_flash",
)

verilog_module(
    name = "strobe_div",
    top = "strobe_div",
    srcs = ["strobe_div.sv"],
)

verilog_module(
    name = "uart_tx",
    top = "uart_tx",
    srcs = ["uart_tx.sv"],
    deps = [":strobe_div"],
)

verilog_module(
    name = "hello_world",
    top = "hello_world",
    srcs = ["hello_world.sv"],
    deps = [
        ":uart_tx",
        ":strobe_div",
    ],
)

# Hello World project prints a message on the serial port of a Digilent Arty A7-35T.

# The .bit, .load, .bin, and .flash targets can be created from the vivado_project macro.
vivado_project(
    name = "hello_world_project",
    module = ":hello_world",
    part = "xc7a35ticsg324-1l",
    io_constraints = [
        "timing_constraints.xdc",
        "io_constraints.xdc",
    ],
    bitstream_constraints = ["bitstream_constraints.xdc"],
    memory_size = 16,
    memory_interface = "SPIx4",
    memory_pn = "mt25ql128-spi-x1_x2_x4",
)

# Or they can be instantiated manually.  Note, the .load and .flash verbs are simply a convention.
vivado_bitstream(
    name = "hello_world.bit",
    module = ":hello_world",
    part = "xc7a35ticsg324-1l",
    io_constraints = [
        "timing_constraints.xdc",
        "io_constraints.xdc",
    ],
    bitstream_constraints = ["bitstream_constraints.xdc"],
)

vivado_config_memory(
    name = "hello_world.bin",
    bitstream = ":hello_world.bit",
    memory_size = 16,
    memory_interface = "SPIx4",
)

vivado_load(
    name = "hello_world.load",
    bitstream = ":hello_world.bit",
)

vivado_flash(
    name = "hello_world.flash",
    config = ":hello_world.bin",
    memory_pn = "mt25ql128-spi-x1_x2_x4",
)
