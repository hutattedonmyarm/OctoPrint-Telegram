# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging, sarge, hashlib, datetime, time, operator, socket
from requests.auth import HTTPBasicAuth
import websocket
import json
import octoprint.filemanager
import requests
from flask.ext.babel import gettext
from .telegramNotifications import telegramMsgDict

class HomeeResponder():
  def __init__(self, telegram, chat_id, logger):
    self._telegram = telegram
    self._chat_id = chat_id
    self._logger = logger
    self._switch_value = -1
    self._error_message = 'Unknown error'
    self._switch_id = 12
    self._attribute_id = 97

  def __call__(self, ws, data, data_type, cont):
    print(ws)
    d = {}
    try:
      d = json.loads(data)
    except ValueError as er:
      self._logger.error("Error parsing switch status: " + str(er))
      self._error_message = 'Could not parse response from Homee'
      self.send_feedback(False)
      ws.close()
      return
    nodes = d.get('all', {}).get('nodes', {})
    node = [node for node in nodes if node.get('id', None) == self._switch_id]
    if len(node) != 1:
      self._logger.error('Found ' + str(len(node)) + 'homee devices with ID ' + str(self._switch_id) + ', but expected 1')
      self._error_message = 'Found ' + str(len(node)) + 'homee devices with ID ' + str(self._switch_id) + ', but expected 1'
      self.send_feedback(False)
      ws.close()
      return
    node = node[0]
    attribute = [attribute for attribute in node['attributes'] if attribute.get('id', None) == self._attribute_id]
    if len(attribute) != 1:
      self._logger.error('Found ' + str(len(attribute)) + 'switch attributes devices with ID ' + str(self._attribute_id) + ', but expected 1')
      self._error_message = 'Found ' + str(len(attribute)) + 'switch attributes with ID ' + str(self._attribute_id) + ', but expected 1'
      self.send_feedback(False)
      ws.close()
      return
    attribute = attribute[0]
    value = None
    try:
      self._logger.debug('Power switch status attribute:')
      self._logger.debug(json.dumps(attribute))
      if 'current_value' not in attribute:
        self._error_message = "Switch doesn't provide it's current status"
      value = attribute.get('current_value', -1)
      self._logger.debug('Power switch value: ' + str(value))
      self._switch_value = int(value)
      self.send_feedback(False)
    except ValueError as er:
      self._logger.error("Unknown power switch value: " + str(value))
      self._logger.error(er)
      self._error_message = "Unknown power switch value: " + str(value)
      self.send_feedback(False)
      ws.close()
      return
    ws.close()
  
  def send_feedback(self, edit_message = True):
    msg = gettext(self.get_value_string())
    msg_id = None
    if edit_message:
      msg_id = self._telegram.getUpdateMsgId(self._chat_id)
    self._logger.error("Sending homee feedback: '" + str(msg) + "', editing message id: " + str(msg_id))
    self._telegram.send_msg(msg, chatID=self._chat_id, msg_id=msg_id,inline=False)

  def get_value_string(self):
    if self._switch_value == -1:
      return 'Power status unknown. ' + self._error_message
    elif self._switch_value == 0:
      return 'Printer is powered off!'
    elif self._switch_value == 1:
      return 'Printer is powered on!'

