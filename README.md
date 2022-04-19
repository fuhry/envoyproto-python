# envoyproto: fetcher/builder for Envoy Python protobuf stubs

This is a set of scripts to fetch, build and package a namespaced version of the [Envoy data plane API](https://github.com/envoyproxy/envoy/tree/main/api). Compiled protobufs go under the `envoyproto` module.

At present, I haven't been able to figure out how to overload the `build` command for `pip`, so this requires some manual steps to set up and build:

* Fetch `envoyproxy/data-plane-api` and its dependencies: `$ git submodule update --init`
* Build the protobuf stubs: (make sure you have `protoc` installed) `python3 setup.py protoc`
* Build and install the module: `sudo python3 setup.py install`
  * Alternatively, build distribution archives: `python3 -m build`

# Quirks

Because this is namespaced, you'll need to rewrite any `google.protobuf.Any` values to `typed_config` used throughout Envoy configuration. This is fairly trivial:

```python
def typed_config(message: google.protobuf.message.Message) -> google.protobuf.any_pb2.Any:
    msg = google.protobuf.any_pb2.Any()
    msg.Pack(message)
    msg.type_url = 'type.googleapis.com/' + msg.type_url.removeprefix('type.googleapis.com/envoyproto.')
    return msg
```

# Author

Dan Fuhry <[dan@fuhry.com](mailto:dan@fuhry.com)>

# License

This project is released under the [Apache License 2.0](LICENSE).
