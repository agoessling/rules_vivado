load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def rules_vivado_direct_deps():
    http_archive(
        name = "rules_verilog",
        strip_prefix = "rules_verilog-0.1.0",
        sha256 = "401b3f591f296f6fd2f6656f01afc1f93111e10b81b9a9d291f9c04b3e4a3e8b",
        url = "https://github.com/agoessling/rules_verilog/archive/v0.1.0.zip",
    )

    http_archive(
	name = "bazel_skylib",
	url = "https://github.com/bazelbuild/bazel-skylib/releases/download/1.0.2/bazel-skylib-1.0.2.tar.gz",
	sha256 = "97e70364e9249702246c0e9444bccdc4b847bed1eb03c5a3ece4f83dfe6abc44",
    )
