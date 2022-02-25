load("@rules_python//python:pip.bzl", "compile_pip_requirements")

exports_files([
    "requirements.txt",
    "requirements.in",
])

compile_pip_requirements(
    name = "requirements",
    extra_args = ["--allow-unsafe"],
)
