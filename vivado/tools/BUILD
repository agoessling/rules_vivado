py_library(
    name = "process_manager",
    srcs = ["process_manager.py"],
)

py_binary(
    name = "vivado_client",
    srcs = ["vivado_client.py"],
    deps = [":process_manager"],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "vivado_server",
    srcs = ["vivado_server.py"],
    deps = [":process_manager"],
    visibility = ["//visibility:public"],
)
