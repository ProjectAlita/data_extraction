#!/usr/bin/python3
# coding=utf-8

""" DataExtractor Plugin Module """

from pylon.core.tools import log, module


class Module(module.ModuleModel):
    """ Plugin Module """

    def __init__(self, context, descriptor):
        self.context = context
        self.descriptor = descriptor

    def init(self):
        """ Initialize the plugin """
        log.info("Initializing DataExtractor Plugin")
        self.descriptor.init_all(
            url_prefix="/",
            static_url_prefix="/",
        )
        log.info("DataExtractor Plugin initialized successfully")

    def deinit(self):
        """ Cleanup when plugin is disabled """
        log.info("Deinitializing DataExtractor Plugin")
