#!/usr/bin/python3
# coding=utf-8

""" Configuration Management """

import os
import pathlib
from pylon.core.tools import log, web


class Method:
    """ Configuration methods """

    @web.method()
    def runtime_config(self):
        """ Get runtime configuration """
        config = {}
        
        # Base configuration
        defaults = {
            # "base_path": "/tmp/dataextractor",
            "base_path": str(pathlib.Path(__file__).parent.parent.joinpath("data", "dataextractor")),
            "service_location_url": "http://127.0.0.1:8080",
            "ui_location_url": "http://127.0.0.1:8080",
            "tool_version": "0.0.0",
        }
        
        # Merge with user config
        for key, default in defaults.items():
            config[key] = self.descriptor.config.get(key, default)
        
        # Ensure paths are absolute
        if "base_path" in config:
            config["base_path"] = os.path.abspath(config["base_path"])
        
        for key, default in defaults.items():
            # Get from config file (which may have env var references)
            value = self.descriptor.config.get(key, default)

            # Handle environment variable references
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_spec = value[2:-1]  # Remove ${ and }
                if ":" in env_spec:
                    env_var, default_val = env_spec.split(":", 1)
                    value = os.getenv(env_var, default_val)
                else:      
                    value = os.getenv(env_spec)
                    if value is None:
                        raise ValueError(f"Required environment variable {env_spec} not set")

            config[key] = value

        return config

    @web.method()
    def setup_directories(self):
        """ Create necessary directories """
        config = self.runtime_config()
        
        if "base_path" in config:
            pathlib.Path(config["base_path"]).mkdir(parents=True, exist_ok=True)
            log.info(f"Created directory: {config['base_path']}")
