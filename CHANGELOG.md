# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.3.1] - 2025-08-24

### Fixed

- Allow omitting staff settings

## [2.3.0] - 2025-08-24

### Fixed

- Published on PyPi now
- Query userinfo for user data (fixes login with Authelia ≥ v4.39.0)

### Added

- Make user staff based on value of OIDC scope

## [2.2.1] - 2025-02-01

### Fixed

- Include CHANGELOG in manifest

## [2.2.0] - 2025-02-01

### Changed

- Move to pyproject.toml

### Added

- Release on PyPi

<!-- markdownlint-disable-file MD024-->

[2.3.0]: https://github.com/thegcat/pretix-oidc/compare/v2.2.1...v2.3.0
[2.2.1]: https://github.com/thegcat/pretix-oidc/compare/v2.2.0...v2.2.1
[2.2.0]: https://github.com/thegcat/pretix-oidc/releases/tag/v2.2.0
