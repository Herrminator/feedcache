
# Feed Cache

[![release][release]](https://github.com/Herrminator/feedcache/releases)
[![tests][unit-tests]](https://github.com/Herrminator/feedcache/actions/workflows/unittests.yml)
[![coverage][coverage]](https://github.com/Herrminator/feedcache/actions/workflows/unittests.yml)
[![build][release-publish]](https://github.com/Herrminator/feedcache/actions/workflows/publish-release.yml)

This small tool was written as a helper for a web based feed reader.
To avoid blocking its batch update process with slow feeds, we decided
to cache some of the slowest (and most error-prone) feeds as local
static XML-files, accessible through a regular https-server.

## Help

Please see the [command line help](./feedcache-help.md).

## Changes

Please see the [change log](./CHANGELOG.md).


<!-- links -->
[unit-tests]:      https://github.com/Herrminator/feedcache/actions/workflows/unittests.yml/badge.svg
[release-publish]: https://github.com/Herrminator/feedcache/actions/workflows/publish-release.yml/badge.svg
[release]:         https://img.shields.io/github/v/release/Herrminator/feedcache?color=blue
<!-- see https://shields.io/badges/endpoint-badge and https://nedbatchelder.com/blog/202209/making_a_coverage_badge.html -->
<!-- use githubusercontent.com, not github.com : https://dev.to/thejaredwilcurt/coverage-badge-with-github-actions-finally-59fa#comment-1g40n-->
[coverage]: https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/Herrminator/088b2618ff7abb97048977a4d632ed54/raw/feedcache-coverage-badge.json
