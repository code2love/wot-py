# WoTPy

## Introduction

This repository contains an experimental implementation of a [W3C WoT Runtime](https://github.com/w3c/wot-architecture/blob/master/terminology.md#wot-runtime) and the [W3C WoT Scripting API](https://w3c.github.io/wot-scripting-api/) in Python.

Inspired by the exploratory implementations located in the [thingweb GitHub page](https://github.com/thingweb).

## Features

* Supports Python 2.7, 3.6 and 3.7.
* Fully-implemented `WoT` interface.
* Multicast discovery based on mDNS.
* Asynchronous I/O programming model based on coroutines.
* Multiple client and server [Protocol Binding](https://github.com/w3c/wot-architecture/blob/master/terminology.md#protocol-binding) implementations. 

WoTPy is based on the [Tornado Framework](https://www.tornadoweb.org). Users therefore have two different APIs to write code based on coroutines: 

* Users on **Python 3** may use the native [asyncio](https://docs.python.org/3/library/asyncio.html) module. This is, in fact, the recommended approach. It should be noted that Tornado on Python 3 acts basically [as a wrapper](https://www.tornadoweb.org/en/stable/asyncio.html) around `asyncio`.
* Users on **Python 2.7** are restricted to writing [Tornado coroutines](https://www.tornadoweb.org/en/stable/guide/coroutines.html) (`asyncio` is not available on Python 2.7).

### Feature support matrix

| Feature            | Python 2.7               | Python 3           | Implementation based on                                                 |
|-------------------:|--------------------------|--------------------|-------------------------------------------------------------------------|
| HTTP binding       | :heavy_check_mark:       | :heavy_check_mark: | [tornadoweb/tornado](https://github.com/tornadoweb/tornado)             |
| WebSockets binding | :heavy_check_mark:       | :heavy_check_mark: | [tornadoweb/tornado](https://github.com/tornadoweb/tornado)             |
| CoAP binding       | :heavy_multiplication_x: | :heavy_check_mark: | [chrysn/aiocoap](https://github.com/chrysn/aiocoap)                     |
| MQTT binding       | :heavy_multiplication_x: | :heavy_check_mark: | [beerfactory/hbmqtt](https://github.com/beerfactory/hbmqtt)             |
| mDNS discovery     | :heavy_multiplication_x: | :heavy_check_mark: | [jstasiak/python-zeroconf](https://github.com/jstasiak/python-zeroconf) |

## ToDo

* Subscription to Thing Description changes.

## Installation

Install in development mode:

```
pip install -U -e .[tests]
```

Run the tests in all supported environments:

```
WOTPY_TESTS_MQTT_BROKER_URL=mqtt://broker-url tox
```

## Docs

Move to the `docs` folder and run:

```
make html
```

If you attempt to build the docs on a non-Linux platform or with Python 2.7 `_autosummary` will complain about being unable to import the unsupported modules (e.g. MQTT on Python 2.7). In this case the docs will be missing the sections regarding unsupported features.