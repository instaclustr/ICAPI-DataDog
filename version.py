import semver, os

# Super simple versioning script for CI
# Default minor version bump
# Major release if '#MAJOR' or '#BREAKING' in last commit
# Patch release if '#PATCH' in last commit
# e.g.
# commit_msg = 'aoeu#patchaoeu' will result in a PATCH version bump.

version = os.popen('git describe --abbrev=0 --tags').read().strip('\n')

commit_msg = os.popen('git log -1').read()

patch = '#PATCH' in commit_msg.upper()
major = '#MAJOR' in commit_msg.upper()
breaking = '#BREAKING' in commit_msg.upper()

new_version = semver.bump_minor(version)

if patch:
    new_version = semver.bump_patch(version)
elif major or breaking:
    new_version = semver.bump_major(version)

print(new_version)
