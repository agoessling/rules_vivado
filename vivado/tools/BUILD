load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "process_manager",
    srcs = ["process_manager.py"],
    deps = [
        requirement("psutil"),
    ],
)

py_binary(
    name = "vivado_client",
    srcs = ["vivado_client.py"],
    visibility = ["//visibility:public"],
    deps = [":process_manager"],
)

py_binary(
    name = "vivado_server",
    srcs = ["vivado_server.py"],
    visibility = ["//visibility:public"],
    deps = [":process_manager"],
)
