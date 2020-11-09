# rules_vivado

Provides [Bazel](https://bazel.build/) rules for
[Xilinx Vivado](https://www.xilinx.com/products/design-tools/vivado.html).

## Usage

### WORKSPACE

To incorporate `rules_vivado` into your project copy the following into your `WORKSPACE` file.

```Starlark
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "rules_vivado",
    # See release page for latest version url and sha.
)

load("@rules_vivado//vivado:direct_repositories.bzl", "rules_vivado_direct_deps")
rules_vivado_direct_deps()

load("@rules_vivado//vivado:indirect_repositories.bzl", "rules_vivado_indirect_deps")
rules_vivado_indirect_deps()
```

### Rules

* `vivado_bitstream` - Creates a bitstream from a module and constraints.
* `vivado_load` - Creates an executable to load a bitstream onto a FPGA.
* `vivado_config_memory` - Creates a configuration memory file from a bitstream.
* `vivado_flash` - Creates an executable to load a configuration memory file to flash.
* `vivado_project` - A macro that ties the above rules together to create `.bit`, `.load`, `.bin`,
  and `.flash` targets in a single invocation. This is suitable for most common use cases.

See [examples/hello_world/BUILD](examples/hello_world/BUILD) for example targets for a Digilent
[Arty
A7-35T](https://reference.digilentinc.com/reference/programmable-logic/arty-a7/reference-manual)
development board.

### Vivado Server

`rules_vivado` works by running the Vivado IDE in Tcl mode as a server
(`vivado_server.py`).  This is advantageous as Vivado takes several (~8 on
development machine) seconds to start up.  The server must be running before building or running any
`rules_vivado` targets:

```Shell
bazel run @rules_vivado//vivado/tools:vivado_server
```

By default `vivado_server.py` assumes the `vivado` executable is availabe on the current `$PATH`.
To provide an explicit path use the `--exec_path` option:

```Shell
bazel run @rules_vivado//vivado/tools:vivado_server -- --exec_path=/path/to/vivado
```

### Vivado Client

The client (`vivado_client.py`) provides a simplified command line interface to the synthesize,
place, route, and program workflow.  The client communicates to the server through sockets.  The
client is invoked automatically by `rules_vivado` to build and run the associated targets, but can
be invoked directly for other use cases:

```Shell
bazel run @rules_vivado//vivado/tools:vivado_client -- command [options]
```
