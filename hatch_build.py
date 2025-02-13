#!/usr/bin/env python3
import os
import re
import typing
import setuptools
import subprocess

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

basedir = os.path.dirname(__file__)

def find_by_extension_recurse(ext, basedir) -> typing.Iterator[str]:
    for entry in os.scandir(basedir):
        if entry.is_file() and entry.path.endswith(ext):
            yield entry.path
        elif entry.is_dir() and os.path.basename(entry.path) not in ['tests']:
            yield from find_by_extension_recurse(ext, entry.path)


def find_protobuf_packages() -> list[str]:
    search_dir = os.path.join(basedir, 'envoyproto')
    if not os.path.isdir(search_dir):
        return []

    packages = set()
    for path in find_by_extension_recurse('_pb2.py', search_dir):
        path = os.path.dirname(path)
        package = path.removeprefix(basedir + os.path.sep).replace(os.path.sep, '.')
        packages.add(package)

    return list(packages)


def compile_protos() -> None:
    proto_namespace_roots = [
        (os.path.join(basedir, 'protobuf-libs', d) + os.path.sep, subtrees)
        for d, subtrees in [
            ('envoy', ['.']),
            ('xds', ['.']),
            ('prometheus-client-model', ['.']),
            ('protoc-gen-validate', ['validate']),
            ('googleapis', ['google/api', 'google/logging', 'google/longrunning', 'google/rpc']),
            ('opentelemetry', ['.']),
            ('opencensus/src', ['.']),
            ('cel/proto', ['cel/expr'])
        ]
    ]

    subs = [
        (r'^package ', 'package envoyproto.'),
        (r'\b(udpa|xds)\.', 'envoyproto.\\1.'),
        (r'\(validate\.(rules|required)\)', '(.envoyproto.validate.\\1)'),
        (r'(\s+)\.envoy\.', '\\1.envoyproto.envoy.'),
        (r'^import (public )?"(envoy|contrib|udpa|xds|validate|google/api|google/logging|google/longrunning|google/rpc|opentelemetry|opencensus|io/prometheus/client|cel/expr|bazel)/', 'import \\1"envoyproto/\\2/'),
        (r'([^\.])google\.protobuf\.', '\\1.google.protobuf.'),
    ]

    for namespace, subtrees in proto_namespace_roots:
        for proto_file_in in find_by_extension_recurse('.proto', namespace):
            subdir = os.path.dirname(proto_file_in[len(namespace):])

            if not '.' in subtrees:
                if not any(subdir.startswith(t + os.path.sep) or subdir == t for t in subtrees):
                    continue

            outpath = os.path.join(basedir, 'envoyproto', subdir)

            proto_file_out = os.path.join(outpath, os.path.basename(proto_file_in))

            if not os.path.isdir(outpath):
                os.makedirs(outpath)

            with open(proto_file_in, 'r') as rfp:
                print('writing %s' % (proto_file_out))
                with open(proto_file_out, 'w') as wfp:
                    for line in rfp:
                        for sub, repl in subs:
                            line = re.sub(sub, repl, line)

                        wfp.write(line)

    for proto_file in find_by_extension_recurse('proto', os.path.join(basedir, 'envoyproto')):
        protoc_cmd = [
            '/usr/bin/protoc',
            f'--python_out={basedir}',
            f'-I{basedir}',
        ] + [
            proto_file
        ]

        out_file = proto_file.removesuffix('.proto') + '_pb2.py'
        should_build = True
        if os.path.exists(out_file):
            if os.stat(out_file).st_mtime >= os.stat(proto_file).st_mtime:
                should_build = False

        if should_build:
            print(' '.join(protoc_cmd))
            subprocess.check_call(protoc_cmd)

    modules: dict[str, list[str]] = {}
    for path in find_by_extension_recurse('_pb2.py', os.path.join(basedir, 'envoyproto')):
        modulepath = os.path.dirname(path)
        if not modulepath in modules:
            modules[modulepath] = []

        modules[modulepath].append(os.path.basename(path).removesuffix('_pb2.py'))

    for path, protos in modules.items():
        init_file = os.path.join(path, '__init__.py')
        print(f'writing {init_file}')
        with open(init_file, 'w') as fp:
            for module in protos:
                fq = path.removeprefix(basedir + os.path.sep).replace(os.path.sep, '.')
                fp.write(f"import {fq}.{module}_pb2 as {module}\n")

            fp.write("\n")
            fp.write("__all__ = ['" + "', '".join(protos) + "']\n")

    master_init_file = os.path.join(basedir, 'envoyproto', '__init__.py')
    with open(master_init_file, 'w') as fp:
        for path, protos in modules.items():
            for module in protos:
                fq = path.removeprefix(basedir + os.path.sep).replace(os.path.sep, '.')
                fp.write(f"import {fq}.{module}_pb2\n")


class ProtobufPyCommand(setuptools.Command):
    """
    Find and build all protobuf files under the envoy API tree.
    """
    description = 'Build protobufs for the envoyproxy API'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        compile_protos()


if __name__ == "__main__":
    compile_protos()

class CustomBuildHook(BuildHookInterface):
    PLUGIN_NAME = "envoyproto-protoc"

    def initialize(self, version, build_data):
        compile_protos()

class CustomMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "envoyproto-meta"

    def update(self, metadata):
        print(repr(self.root))
        print(repr(self.config))
        print(repr(metadata))
