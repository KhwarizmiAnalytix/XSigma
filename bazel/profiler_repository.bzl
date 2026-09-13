"""Local checkout of ThirdParty/Profiler with XSigma's overlay BUILD.

The vendored repo ships its own BUILD.bazel files that refer to in-repo
//Packages labels. new_local_repository would keep those nested packages.
This rule copies the tree, drops nested BUILD files, and writes
//ThirdParty:profiler.BUILD at the root so @xsigma//bazel flags apply.

Kineto and ITT are private to Profiler: their BUILD overlays are written
under third_party/{kineto,ittapi}/ inside the staged @profiler repo so
XSigma never registers @kineto / @ittapi WORKSPACE dependencies.
"""

def _local_profiler_repository_impl(repository_ctx):
    src = repository_ctx.path(str(repository_ctx.workspace_root) + "/" + repository_ctx.attr.path)
    if not src.exists:
        fail("Profiler checkout missing at %s (git submodule update --init ThirdParty/Profiler)" % src)

    kineto_src = repository_ctx.path(str(src) + "/third_party/kineto/libkineto")
    itt_src = repository_ctx.path(str(src) + "/third_party/ittapi")
    if not kineto_src.exists or not itt_src.exists:
        fail(
            "Profiler nested third_party (kineto/ittapi) missing. Initialize:\n" +
            "  git submodule update --init --recursive ThirdParty/Profiler"
        )

    python = repository_ctx.which("python3")
    if python == None:
        python = repository_ctx.which("python")
    if python == None:
        fail("python3 is required to stage @profiler")

    # Prefer rsync: skips ittapi's circular rust/c-library symlink and unused trees.
    rsync = repository_ctx.which("rsync")
    if rsync != None:
        result = repository_ctx.execute([
            rsync,
            "-a",
            "--copy-links",
            "--exclude", ".git",
            "--exclude", "third_party/ittapi/rust",
            "--exclude", "third_party/ittapi/python",
            "--exclude", "third_party/kineto/tb_plugin",
            "--exclude", "third_party/kineto/benchmarks",
            # libkineto's nested third_party (dynolog, …) is unused by our
            # kineto.BUILD overlay and ships invalid/non-Bazel BUILD files.
            "--exclude", "third_party/kineto/libkineto/third_party",
            str(src) + "/",
            "./",
        ])
        if result.return_code != 0:
            fail("Failed to rsync Profiler sources: %s%s" % (result.stdout, result.stderr))
    else:
        copy_script = """
import os
import shutil
import sys

src, dst = sys.argv[1], sys.argv[2]

def _ignore(directory, names):
    ignored = []
    parts = directory.replace("\\\\", "/").split("/")
    if "ittapi" in parts:
        for name in ("rust", "python"):
            if name in names:
                ignored.append(name)
    if "kineto" in parts and parts[-1] == "kineto":
        for name in ("tb_plugin", "benchmarks"):
            if name in names:
                ignored.append(name)
    return ignored

for name in os.listdir(src):
    s = os.path.join(src, name)
    d = os.path.join(dst, name)
    if os.path.isdir(s):
        shutil.copytree(s, d, ignore=_ignore, symlinks=False)
    elif not os.path.islink(s):
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

    # Drop vendored nested BUILD files under third_party (kineto dynolog, etc.)
    # so @profiler//... does not analyze unrelated packages. We re-add only the
    # private kineto/ittapi overlays below.
    strip_script = """
import os
import sys
root = sys.argv[1]
for dirpath, dirnames, filenames in os.walk(os.path.join(root, "third_party")):
    for name in filenames:
        if name in ("BUILD", "BUILD.bazel", "WORKSPACE", "WORKSPACE.bazel"):
            os.remove(os.path.join(dirpath, name))
"""
    strip = repository_ctx.execute([python, "-c", strip_script, "."])
    if strip.return_code != 0:
        fail("Failed to strip nested BUILD files: %s%s" % (strip.stdout, strip.stderr))

    # Private backend BUILD overlays (content lives under //ThirdParty as
    # templates; not registered as top-level WORKSPACE repos).
    repository_ctx.file(
        "third_party/kineto/BUILD.bazel",
        repository_ctx.read(repository_ctx.attr.kineto_build_file),
    )
    repository_ctx.file(
        "third_party/ittapi/BUILD.bazel",
        repository_ctx.read(repository_ctx.attr.ittapi_build_file),
    )

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
        "kineto_build_file": attr.label(mandatory = True, allow_single_file = True),
        "ittapi_build_file": attr.label(mandatory = True, allow_single_file = True),
    },
    local = True,
)
