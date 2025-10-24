# robot/webrtc.py
import asyncio
import json
import time
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.rtcdatachannel import RTCDataChannel

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class WebRTCBridge(Node):
    def __init__(self):
        super().__init__("webrtc_client")

        # Declare ROS params with defaults
        self.declare_parameter("robot_id", "robot-001")
        self.declare_parameter("signaling_url", "wss://polyflow.studio/signal")
        self.declare_parameter("auth_token", "")

        self.robot_id = self.get_parameter("robot_id").get_parameter_value().string_value
        self.signaling_url = self.get_parameter("signaling_url").get_parameter_value().string_value
        self.auth_token = self.get_parameter("auth_token").get_parameter_value().string_value

        self.get_logger().info(f"WebRTC client starting for robot_id={self.robot_id}, signaling={self.signaling_url}")

        # ROS pubs/subs
        self.j1_cmd_pub = self.create_publisher(Float32, "/arm/j1/cmd/position", 10)
        self.j1_state_sub = self.create_subscription(
            Float32, "/arm/j1/state/position", self._on_j1_state, 10
        )

        # Holds outbound state channel
        self.state_channel: RTCDataChannel | None = None

    # === ROS Callbacks ===
    def _on_j1_state(self, msg: Float32):
        """When robot publishes state, send it over WebRTC state channel."""
        if self.state_channel and self.state_channel.readyState == "open":
            env = {
                "topic": "robot/arm/j1/state/position",
                "qos": "state",
                "tUnixNanos": int(time.time() * 1e9),
                "payload": {"positionRad": float(msg.data)},
            }
            try:
                self.state_channel.send(json.dumps(env))
            except Exception as e:
                self.get_logger().warn(f"Failed to send state: {e}")

    # === Control handler ===
    def on_control_message(self, data: str):
        try:
            env = json.loads(data)
        except Exception:
            return
        topic = env.get("topic", "")
        if topic == "robot/arm/j1/cmd/position":
            pos = float(env["payload"]["positionRad"])
            msg = Float32()
            msg.data = pos
            self.j1_cmd_pub.publish(msg)
            self.get_logger().info(f"Received control: j1 position={pos}")


async def run_webrtc(node: WebRTCBridge):
    """Main async WebRTC loop."""

    url = node.signaling_url
    if node.auth_token:
        url = f"{url}?token={node.auth_token}"

    async with websockets.connect(url) as ws:
        await ws.send(
            json.dumps({"type": "hello", "role": "robot", "robotId": node.robot_id})
        )

        pc = RTCPeerConnection()

        # Handle incoming DataChannels
        @pc.on("datachannel")
        def on_datachannel(channel: RTCDataChannel):
            node.get_logger().info(f"DataChannel opened: {channel.label}")
            if channel.label == "control":
                @channel.on("message")
                def on_message(message):
                    if isinstance(message, bytes):
                        message = message.decode("utf-8", "ignore")
                    node.on_control_message(message)
            elif channel.label == "state":
                node.state_channel = channel

        # Handle signaling messages
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "offer":
                await pc.setRemoteDescription(
                    RTCSessionDescription(sdp=msg["sdp"], type="offer")
                )
                answer = await pc.createAnswer()
                await pc.setLocalDescription(answer)
                await ws.send(
                    json.dumps(
                        {
                            "type": "answer",
                            "robotId": node.robot_id,
                            "sdp": pc.localDescription.sdp,
                            "to": msg["from"],
                        }
                    )
                )
            elif msg["type"] == "candidate":
                try:
                    await pc.addIceCandidate(msg["candidate"])
                except Exception:
                    pass


def main(args=None):
    rclpy.init(args=args)
    node = WebRTCBridge()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run_webrtc(node))
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
