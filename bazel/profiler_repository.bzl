"""Local checkout of ThirdParty/Profiler with XSigma's overlay BUILD.

The vendored repo ships its own BUILD.bazel files that refer to in-repo
//Packages labels. new_local_repository would keep those nested packages.
This rule copies the tree, drops nested BUILD files, and writes
//ThirdParty:profiler.BUILD at the root so @xsigma//bazel flags apply.
"""

def _local_profiler_repository_impl(repository_ctx):
    src = repository_ctx.path(str(repository_ctx.workspace_root) + "/" + repository_ctx.attr.path)
    if not src.exists:
        fail("Profiler checkout missing at %s (git submodule update --init ThirdParty/Profiler)" % src)

    python = repository_ctx.which("python3")
    if python == None:
        python = repository_ctx.which("python")
    if python == None:
        fail("python3 is required to stage @profiler")

    copy_script = """
import os
import shutil
import sys

src, dst = sys.argv[1], sys.argv[2]
for name in os.listdir(src):
    s = os.path.join(src, name)
    d = os.path.join(dst, name)
    if os.path.isdir(s):
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)
"""
    result = repository_ctx.execute([python, "-c", copy_script, str(src), "."])
    if result.return_code != 0:
        fail("Failed to copy Profiler sources: %s%s" % (result.stdout, result.stderr))

    for rel in [
        "BUILD.bazel",
        "WORKSPACE.bazel",
        "Testing/BUILD.bazel",
        "Testing/Cxx/BUILD.bazel",
    ]:
        nested = repository_ctx.path(rel)
        if nested.exists:
            repository_ctx.delete(nested)

    repository_ctx.file(
        "WORKSPACE",
        'workspace(name = "%s")\n' % repository_ctx.name,
    )
    repository_ctx.file(
        "BUILD.bazel",
        repository_ctx.read(repository_ctx.attr.build_file),
    )

local_profiler_repository = repository_rule(
    implementation = _local_profiler_repository_impl,
    attrs = {
        "path": attr.string(mandatory = True),
        "build_file": attr.label(mandatory = True, allow_single_file = True),
    },
    local = True,
)
