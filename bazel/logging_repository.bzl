"""Local checkout of ThirdParty/Logging with XSigma's overlay BUILD.

new_local_repository would keep Logging/ThirdParty/BUILD.bazel as a nested
package, which blocks the overlay from compiling nested loguru/glog/spdlog
sources. This rule copies the tree, drops nested BUILD files, and writes
//ThirdParty:logging.BUILD at the root so backends stay private to @logging.
"""

def _local_logging_repository_impl(repository_ctx):
    src = repository_ctx.path(str(repository_ctx.workspace_root) + "/" + repository_ctx.attr.path)
    if not src.exists:
        fail("Logging checkout missing at %s (git submodule update --init ThirdParty/Logging)" % src)

    loguru_src = repository_ctx.path(str(src) + "/ThirdParty/loguru/loguru.cpp")
    if not loguru_src.exists:
        fail(
            "Logging nested ThirdParty backends missing. Initialize:\n" +
            "  git submodule update --init --recursive ThirdParty/Logging"
        )

    python = repository_ctx.which("python3")
    if python == None:
        python = repository_ctx.which("python")
    if python == None:
        fail("python3 is required to stage @logging")

    rsync = repository_ctx.which("rsync")
    if rsync != None:
        result = repository_ctx.execute([
            rsync,
            "-a",
            "--copy-links",
            "--exclude", ".git",
            str(src) + "/",
            "./",
        ])
        if result.return_code != 0:
            fail("Failed to rsync Logging sources: %s%s" % (result.stdout, result.stderr))
    else:
        copy_script = """
import os
import shutil
import sys
src, dst = sys.argv[1], sys.argv[2]
for name in os.listdir(src):
    s, d = os.path.join(src, name), os.path.join(dst, name)
    if os.path.isdir(s):
        shutil.copytree(s, d, symlinks=False)
    elif not os.path.islink(s):
        shutil.copy2(s, d)
"""
        result = repository_ctx.execute([python, "-c", copy_script, str(src), "."])
        if result.return_code != 0:
            fail("Failed to copy Logging sources: %s%s" % (result.stdout, result.stderr))

    for rel in [
        "BUILD.bazel",
        "WORKSPACE.bazel",
        "Testing/BUILD.bazel",
        "Testing/Cxx/BUILD.bazel",
        # Standalone Logging ignores nested backends because they are separate
        # WORKSPACE repos there. This overlay compiles them in-tree, so the
        # ignore file must not hide those sources from glob().
        ".bazelignore",
    ]:
        nested = repository_ctx.path(rel)
        if nested.exists:
            repository_ctx.delete(nested)

    # Drop nested BUILD files under ThirdParty/ so loguru/glog/spdlog sources
    # are not a separate Bazel package. Keep bazel/BUILD.bazel (config_settings).
    strip_script = """
import os
import sys
root = os.path.join(sys.argv[1], "ThirdParty")
if os.path.isdir(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            if name in ("BUILD", "BUILD.bazel", "WORKSPACE", "WORKSPACE.bazel"):
                os.remove(os.path.join(dirpath, name))
"""
    strip = repository_ctx.execute([python, "-c", strip_script, "."])
    if strip.return_code != 0:
        fail("Failed to strip nested BUILD files: %s%s" % (strip.stdout, strip.stderr))

    repository_ctx.file(
        "WORKSPACE",
        'workspace(name = "%s")\n' % repository_ctx.name,
    )
    repository_ctx.file(
        "BUILD.bazel",
        repository_ctx.read(repository_ctx.attr.build_file),
    )

local_logging_repository = repository_rule(
    implementation = _local_logging_repository_impl,
    attrs = {
        "path": attr.string(mandatory = True),
        "build_file": attr.label(mandatory = True, allow_single_file = True),
    },
    local = True,
)
