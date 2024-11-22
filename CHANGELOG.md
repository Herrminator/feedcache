# Change Log

## 1.6.0 (2024-11-22):
  + Add unit tests.
  + Allow `file://`-URLs for feeds (mainly for tests).
  + Add GitHub actions for unit tests and releasing.
  - Fix some minor bugs discovered by unit testing.
  * Use a version number higher than the `feedcache` from PyPi. I'm not planning to publish...

## 0.1.6:
  * Avoid third-party log spamming by using a named logger.

## 0.1.5:
  + Add proxy support if python-requests is installed.

## 0.1.4:
  - fix logging for feed-verification errors

## 0.1.3:
  * Increase HTTP response snippet length in error logs
  * Normalize CR/LF for content comparison

## 0.1.2:
  - actually *use* global timeout
  + command line option --version
  - remove `__main__.py` from root

## 0.1.1:
  * actually log errors with level `ERROR` ;)

## 0.1.0:
  + wheel installer
  + number of threads configurable
  * implement as python module, code reorganization

## 0.0.1:
  * single python script ~~(see `TODO.txt`)~~

## 0.0.0:
  + bash script version