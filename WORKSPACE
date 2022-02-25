workspace(name = "rules_vivado")

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("@rules_vivado//vivado:direct_repositories.bzl", "rules_vivado_direct_deps")

rules_vivado_direct_deps()

load("@rules_vivado//vivado:indirect_repositories.bzl", "rules_vivado_indirect_deps")

rules_vivado_indirect_deps()

http_archive(
    name = "rules_python",
    sha256 = "cd6730ed53a002c56ce4e2f396ba3b3be262fd7cb68339f0377a45e8227fe332",
    urls = [
        "https://github.com/bazelbuild/rules_python/releases/download/0.5.0/rules_python-0.5.0.tar.gz",
        "https://mirror.bazel.build/github.com/bazelbuild/rules_python/releases/download/0.5.0/rules_python-0.5.0.tar.gz",
    ],
)

load("@rules_python//python:pip.bzl", "pip_parse")

pip_parse(
    name = "pip",
    requirements_lock = "//:requirements.txt",
)

load("@pip//:requirements.bzl", "install_deps")

install_deps()
