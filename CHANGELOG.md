# Changelog: Version 5.0.2-LTS &mdash; Async Expansion

**Date:** September 1, 2025

Zerionyx 5.0.2-LTS is the second Long-Term Support (LTS) release in the 5.0.x series.
This update expands the asynchronous standard library (`libs.asyncio`) with a rich set of coroutine-based utilities, making concurrent programming more practical and powerful for production use.

---

## ✨ New Features

* **`libs.asyncio` Enhancements**
  Added a comprehensive set of asynchronous functions:

  * **sleep(duration)** &rarr; Non-blocking sleep for a given number of seconds
  * **gather(coroutines\_list)** &rarr; Run multiple coroutines concurrently and collect results
  * **timeout(coroutine, ms)** &rarr; Run a coroutine with a timeout (milliseconds)
  * **timeouts(coroutines\_list, ms)** &rarr; Run multiple coroutines concurrently with a shared timeout
  * **read(file\_path, mode)** &rarr; Async file read
  * **write(file\_path, mode, content)** &rarr; Async file write
  * **copy(source, destination)** &rarr; Async file copy
  * **walk(directory)** &rarr; Async directory tree traversal
  * **list\_dir(directory)** &rarr; Async directory listing
  * **get\_ip()** &rarr; Retrieve public IP address asynchronously
  * **ping(host)** &rarr; Ping host, returning true/false asynchronously
  * **downl(url, timeout=15)** &rarr; Download file from URL asynchronously
  * **request(url, method="GET", headers={}, data={}, timeout=15)** &rarr; Async HTTP request
  * **system(command)** &rarr; Execute system command asynchronously
  * **osystem(command)** &rarr; Execute system command asynchronously and capture output
  * **wait\_key(key)** &rarr; Wait for keyboard key press asynchronously
  * **capture\_screen(path)** &rarr; Capture full screen asynchronously
  * **capture\_area(x, y, w, h, path)** &rarr; Capture a screen region asynchronously
  * **send(channel, value)** &rarr; Send value to a channel asynchronously
  * **receive(channel)** &rarr; Receive value from a channel asynchronously
  * **is\_panic(func, args=\[], kwargs={})** &rarr; Execute function asynchronously with error-catching

---

## 🛠 Bug Fixes

* **Threading Library**
  Fixed critical issues in `libs.threading` where:

  * Deadlocks could occur under high-concurrency workloads.
  * Race conditions in thread joining occasionally caused inconsistent results.
  * Error reporting has been improved for better debugging of multi-threaded apps.

---

Zerionyx 5.0.2-LTS further empowers developers by making asynchronous workflows first-class citizens, while also delivering key threading fixes for improved stability.

