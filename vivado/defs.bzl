load("@bazel_skylib//lib:paths.bzl", "paths")
load("@rules_verilog//verilog:defs.bzl", "VerilogModuleInfo")

VivadoInfo = provider(
    doc = "Info pertaining to Vivado target.",
    fields = ["part"],
)

def _vivado_bitstream_impl(ctx):
    name, ext = paths.split_extension(ctx.label.name)
    if not ext:
        ext = ".bit"

    common_args = ["-p", ctx.attr.part]

    post_synth = ctx.actions.declare_file("{}_post_synth.dcp".format(name))

    synth_args = ctx.actions.args()
    synth_args.add("synth")
    synth_args.add_all(common_args)
    synth_args.add_all("--tcl", ctx.files.pre_synth_tcl)
    synth_args.add("-t", ctx.attr.module[VerilogModuleInfo].top)
    synth_args.add_all("-v", ctx.attr.module[VerilogModuleInfo].files)
    synth_args.add("-o", post_synth)

    ctx.actions.run(
        outputs = [post_synth],
        inputs = ctx.files.pre_synth_tcl + ctx.attr.module[VerilogModuleInfo].files.to_list(),
        executable = ctx.attr._vivado_client[DefaultInfo].files_to_run,
        arguments = [synth_args],
        mnemonic = "VivadoSynth",
        progress_message = "Synthesizing {}".format(ctx.attr.module[VerilogModuleInfo].top),
    )

    post_place = ctx.actions.declare_file("{}_post_place.dcp".format(name))

    place_args = ctx.actions.args()
    place_args.add("place")
    place_args.add_all(common_args)
    place_args.add_all("--tcl", ctx.files.pre_place_tcl)
    place_args.add_all("-c", ctx.files.io_constraints)
    place_args.add("-i", post_synth)
    place_args.add("-o", post_place)

    ctx.actions.run(
        outputs = [post_place],
        inputs = ctx.files.io_constraints + [post_synth] + ctx.files.pre_place_tcl,
        executable = ctx.attr._vivado_client[DefaultInfo].files_to_run,
        arguments = [place_args],
        mnemonic = "VivadoPlace",
        progress_message = "Placing {}".format(ctx.attr.module[VerilogModuleInfo].top),
    )

    post_route = ctx.actions.declare_file("{}_post_route.dcp".format(name))

    route_args = ctx.actions.args()
    route_args.add("route")
    route_args.add_all(common_args)
    route_args.add_all("--tcl", ctx.files.pre_route_tcl)
    route_args.add("-i", post_place)
    route_args.add("-o", post_route)

    ctx.actions.run(
        outputs = [post_route],
        inputs = [post_place] + ctx.files.pre_route_tcl,
        executable = ctx.attr._vivado_client[DefaultInfo].files_to_run,
        arguments = [route_args],
        mnemonic = "VivadoRoute",
        progress_message = "Routing {}".format(ctx.attr.module[VerilogModuleInfo].top),
    )

    bitstream = ctx.actions.declare_file("{}{}".format(name, ext))

    bitstream_args = ctx.actions.args()
    bitstream_args.add("bitstream")
    bitstream_args.add_all(common_args)
    bitstream_args.add("--check")
    bitstream_args.add_all("-c", ctx.files.bitstream_constraints)
    bitstream_args.add("-i", post_route)
    bitstream_args.add("-o", bitstream)

    ctx.actions.run(
        outputs = [bitstream],
        inputs = ctx.files.bitstream_constraints + [post_route],
        executable = ctx.attr._vivado_client[DefaultInfo].files_to_run,
        arguments = [bitstream_args],
        mnemonic = "VivadoBitstream",
        progress_message = "Generating bitstream for {}".format(ctx.attr.module[VerilogModuleInfo].top),
    )

    return [
        DefaultInfo(files = depset([bitstream])),
        VivadoInfo(part = ctx.attr.part),
    ]

vivado_bitstream = rule(
    implementation = _vivado_bitstream_impl,
    doc = "Generate Vivado bitstream.",
    attrs = {
        "module": attr.label(
            doc = "Module for bitstream.",
            mandatory = True,
            providers = [VerilogModuleInfo],
        ),
        "part": attr.string(
            doc = "Xilinx part number.",
            mandatory = True,
        ),
        "io_constraints": attr.label_list(
            doc = "Xilinx constraints for placement.",
            mandatory = True,
            allow_empty = False,
            allow_files = [".xdc"],
        ),
        "pre_synth_tcl": attr.label_list(
            doc = "Tcl sources to run before synthesis.",
            allow_files = [".tcl"],
        ),
        "pre_place_tcl": attr.label_list(
            doc = "Tcl sources to run before placement.",
            allow_files = [".tcl"],
        ),
        "pre_route_tcl": attr.label_list(
            doc = "Tcl sources to run before routing.",
            allow_files = [".tcl"],
        ),
        "bitstream_constraints": attr.label_list(
            doc = "Xilinx constraints for bitstream generation.",
            mandatory = True,
            allow_empty = False,
            allow_files = [".xdc"],
        ),
        "_vivado_client": attr.label(
            doc = "Vivado client executable.",
            default = Label("@rules_vivado//vivado/tools:vivado_client"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def _vivado_config_memory_impl(ctx):
    name, ext = paths.split_extension(ctx.label.name)
    if not ext:
        ext = ".bin"

    config_memory = ctx.actions.declare_file("{}{}".format(name, ext))

    config_args = ctx.actions.args()
    config_args.add("cfg_mem")
    config_args.add("-p", ctx.attr.bitstream[VivadoInfo].part)
    config_args.add("--size", str(ctx.attr.memory_size))
    config_args.add("--interface", ctx.attr.memory_interface)
    config_args.add_all("-i", ctx.attr.bitstream[DefaultInfo].files)
    config_args.add("-o", config_memory)

    ctx.actions.run(
        outputs = [config_memory],
        inputs = ctx.attr.bitstream[DefaultInfo].files,
        executable = ctx.attr._vivado_client[DefaultInfo].files_to_run,
        arguments = [config_args],
        mnemonic = "VivadoCfgMem",
        progress_message = "Generating configuration memory",
    )
    return [
        DefaultInfo(files = depset([config_memory])),
        ctx.attr.bitstream[VivadoInfo],
    ]

vivado_config_memory = rule(
    implementation = _vivado_config_memory_impl,
    doc = "Generate Vivado configuration memory.",
    attrs = {
        "bitstream": attr.label(
            doc = "Vivado bitstream.",
            mandatory = True,
            allow_single_file = True,
            providers = [
                DefaultInfo,
                VivadoInfo,
            ],
        ),
        "memory_size": attr.int(
            doc = "Configuration memory size in MB.",
            mandatory = True,
        ),
        "memory_interface": attr.string(
            doc = "Configuration memory interface.",
            mandatory = True,
            values = [
                "SMAPx8",
                "SMAPx16",
                "SMAPx32",
                "SERIALx1",
                "SPIx1",
                "SPIx2",
                "SPIx4",
                "SPIx8",
                "BPIx8",
                "BPIx16",
            ],
        ),
        "_vivado_client": attr.label(
            doc = "Vivado client executable.",
            default = Label("@rules_vivado//vivado/tools:vivado_client"),
            executable = True,
            cfg = "exec",
        ),
    },
)

def _vivado_load_impl(ctx):
    shell_cmd = [
        ctx.executable._vivado_client.short_path,
        "load",
        "-p",
        ctx.attr.bitstream[VivadoInfo].part,
        "-i",
        " ".join([f.short_path for f in ctx.attr.bitstream[DefaultInfo].files.to_list()]),
    ]

    script = ctx.actions.declare_file("{}.sh".format(ctx.label.name))
    ctx.actions.write(script, " ".join(shell_cmd), is_executable = True)

    runfiles = ctx.runfiles(
        transitive_files = depset(
            transitive = [
                ctx.attr._vivado_client[DefaultInfo].default_runfiles.files,
                ctx.attr.bitstream[DefaultInfo].files,
            ],
        ),
    )
    return [DefaultInfo(executable = script, runfiles = runfiles)]

vivado_load = rule(
    implementation = _vivado_load_impl,
    doc = "Load bitstream onto part.",
    attrs = {
        "bitstream": attr.label(
            doc = "Vivado bitstream.",
            mandatory = True,
            allow_single_file = True,
            providers = [
                DefaultInfo,
                VivadoInfo,
            ],
        ),
        "_vivado_client": attr.label(
            doc = "Vivado client executable.",
            default = Label("@rules_vivado//vivado/tools:vivado_client"),
            executable = True,
            cfg = "exec",
        ),
    },
    executable = True,
)

def _vivado_flash_impl(ctx):
    shell_cmd = [
        ctx.executable._vivado_client.short_path,
        "flash",
        "-p",
        ctx.attr.config[VivadoInfo].part,
        "--memory",
        ctx.attr.memory_pn,
        "-i",
        " ".join([f.short_path for f in ctx.attr.config[DefaultInfo].files.to_list()]),
    ]

    script = ctx.actions.declare_file("{}.sh".format(ctx.label.name))
    ctx.actions.write(script, " ".join(shell_cmd), is_executable = True)

    runfiles = ctx.runfiles(
        transitive_files = depset(
            transitive = [
                ctx.attr._vivado_client[DefaultInfo].default_runfiles.files,
                ctx.attr.config[DefaultInfo].files,
            ],
        ),
    )
    return [DefaultInfo(executable = script, runfiles = runfiles)]

vivado_flash = rule(
    implementation = _vivado_flash_impl,
    doc = "Load configuration memory onto part.",
    attrs = {
        "config": attr.label(
            doc = "Vivado configuration memory file.",
            mandatory = True,
            allow_single_file = True,
            providers = [
                DefaultInfo,
                VivadoInfo,
            ],
        ),
        "memory_pn": attr.string(
            doc = "Memory part number.",
            mandatory = True,
        ),
        "_vivado_client": attr.label(
            doc = "Vivado client executable.",
            default = Label("@rules_vivado//vivado/tools:vivado_client"),
            executable = True,
            cfg = "exec",
        ),
    },
    executable = True,
)

def vivado_project(
        name,
        module,
        part,
        io_constraints,
        bitstream_constraints,
        memory_size,
        memory_interface,
        memory_pn):
    vivado_bitstream(
        name = "{}.bit".format(name),
        module = module,
        part = part,
        io_constraints = io_constraints,
        bitstream_constraints = bitstream_constraints,
    )

    vivado_load(
        name = "{}.load".format(name),
        bitstream = ":{}.bit".format(name),
    )

    vivado_config_memory(
        name = "{}.bin".format(name),
        bitstream = ":{}.bit".format(name),
        memory_size = memory_size,
        memory_interface = memory_interface,
    )

    vivado_flash(
        name = "{}.flash".format(name),
        config = ":{}.bin".format(name),
        memory_pn = memory_pn,
    )
