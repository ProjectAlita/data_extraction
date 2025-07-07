#!/usr/bin/python3
# coding=utf-8

""" Health Check Route """

import time
import datetime
from pylon.core.tools import web


class Route:
    """ Health check route """

    @web.route("/health")
    def health_route(self):
        """ Return plugin health status """
        try:
            current_time = time.time()
            uptime = current_time - getattr(self, 'start_time', current_time)
            
            config = self.runtime_config()
            
            return {
                "status": "UP",
                "providerVersion": "1.0.0", 
                "uptime": int(uptime),
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00"),
                "plugin": "DataExtractor",
                "configuration": config,
                "extra_info": {},
            }
        except Exception as e:
            return {
                "status": "DOWN",
                "error": str(e)
            }, 500
