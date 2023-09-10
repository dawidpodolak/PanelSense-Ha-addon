from mediator.components.base_component import BaseComponent
from homeassistant.model.ha_message import HaEventData
from mediator.components.light.state import LightState
from mediator.components.light.light_model import LightModel
from server.model.server_message import LightMessage
from typing import Optional


class Light(BaseComponent):

    state = LightState()

    def __init__(self, haEventData: Optional[HaEventData] = None, light_message: Optional[LightMessage] = None):
        if haEventData:
            self.updateState(haEventData)
        elif light_message:
            self.update_state_from_server(light_message)

    def updateState(self, haEventData: HaEventData):
        self.entity_id = haEventData.entity_id
        self.state.on = haEventData.new_state.state == 'on'
        self.state.brightness = haEventData.new_state.attributes.brightness
        self.state.color_mode = haEventData.new_state.attributes.color_mode
        self.state.effect = haEventData.new_state.attributes.effect
        self.state.effect_list = haEventData.new_state.attributes.effect_list
        self.state.friendly_name = haEventData.new_state.attributes.friendly_name
        self.state.hs_color = haEventData.new_state.attributes.hs_color
        self.state.min_color_temp_kelvin = haEventData.new_state.attributes.min_color_temp_kelvin
        self.state.max_color_temp_kelvin = haEventData.new_state.attributes.max_color_temp_kelvin
        self.state.min_mireds = haEventData.new_state.attributes.min_mireds
        self.state.max_mireds = haEventData.new_state.attributes.max_mireds
        self.state.rgb_color = haEventData.new_state.attributes.rgb_color
        self.state.supported_color_modes = haEventData.new_state.attributes.supported_color_modes
        self.state.supported_features = haEventData.new_state.attributes.supported_features

    def getHomeAssistantMessage(self) -> str:
        return "This is test!"

    def getSenseServerMessage(self):
        return LightModel(
            entity_id=self.entity_id,
            state=self.state
        )

    def update_state_from_server(self, light_message: LightMessage):
        self.entity_id = light_message.entity_id
        self.state.on = light_message.state.on
        print(
            f"update_state_from_server: entity_id: {self.entity_id}, state: {self.state.on}")
