# radish
Radish is a tool for listening to and controlling Daikin HVAC systems locally. Currently, it is only able to sniff the raw RS-485 messages that are passed around between devices like a thermostat, air handler, and outdoor unit and relay them over MQTT, but its capabilities will grow over time.

## Parts
- [AtomS3 Lite](https://shop.m5stack.com/products/atoms3-lite-esp32s3-dev-kit): WiFi chip and brain
- [Tail485](https://shop.m5stack.com/products/atom-tail485): RS-485 converter
- 12V power supply ([random example](https://www.amazon.com/inShareplus-Mounted-Switching-Connector-Adapter/dp/B01GD4ZQRS))

Other ESP32s would also work, as would an RS-485 converter such as the MAX485, but the M5Stack products are cheap enough and have a nice form factor. 

Other RS-485 options from M5Stack:
- The [Atomic 485 Base](https://shop.m5stack.com/products/atomic-rs485-base) would allow you to power things through a USB-C cable instead of a 12V power supply, though it uses most of the GPIO pins.
- The [RS485 to TTL Converter Unit](https://shop.m5stack.com/products/rs485-module) would also avoid blocking the USB-C port.
- The [Isolated RS485 Unit](https://shop.m5stack.com/products/isolated-rs485-unit) is similar, but is probably the safest way to make sure you don't break your HVAC system.

## Software Prerequisites
Once you have your ESP32, you can connect it to Home Assistant or another device with a USB cable. Flash it with [ESPHome](https://esphome.io/) and something similar to [radish.yaml](radish.yaml). If all goes well, you'll be able to see it on your network, and the LED will light up red when you click the main button.

You'll also need an MQTT broker on your network. In my case, I'm using the [Mosquitto app](https://www.home-assistant.io/integrations/mqtt/) for Home Assistant.

## Physical Setup
Connect the Tail485 to the 12V power supply, double-checking its polarity, and connect the A and B terminals to the Data 1 and Data 2 wires that go between your devices. The easiest way may be by connecting additional wires to the thermostat screw terminals, but for a cleaner look, you may try from the air handler or from any splices in the thermostat wire along the way. Be sure not to use the R and C wires, or to even let any bare wires touch each other, or you may fry your boards, blow a fuse, or break even more expensive things. It may be safer to cut power to the system before attempting this. Once everything's connected, you can power your system back on, plug in the power supply, and connect the Atom to the Tail. If you see the red light when clicking the button, things should be good to go.

## Initial Data
If you've installed Mosquitto on your local machine, you may then be able to run a command similar to `mosquitto_sub -h <mqtt broker ip address> -u <mqtt username> -P <mqtt password> -t radish/rs485/raw`. 

If you see a variety of packets of bytes printing out, at a rate of every few seconds to a couple of times per second, you're probably in luck. If you don't see anything, check that everything is wired and powered correctly, and check that your thermostat isn't experiencing a communication error, which could be a sign of a deeper issue, like a ground loop. If that's the case, __immediately__ disconnect the Tail from the system. If you're getting data, but most of the bytes seem to be `FF`, you may have your data wires swapped, and you can either physically switch them or swap the TX and RX GPIO pins in the YAML and reupload it.

## Parsing
An initial attempt at parsing the data is found in `mqtt_listener.py`. To use it, install the project's Python requirements and then copy `.env.example` to `.env` and set the environment variables within it.

## References
A big thanks to [@rrmayer](https://github.com/rrmayer) for sharing the ClimateTalk docs in his [climate-talk-web-api](https://github.com/rrmayer/climate-talk-web-api) repo and to [@kdschlosser](https://github.com/kdschlosser) for his own [ClimateTalk](https://github.com/kdschlosser/ClimateTalk) repo.

## TODO:
- Verify all messages.
- Figure out MDI
- Determine why R2R ACK is appearing in random messages. It seems to be an ACK and only appears when the packet number indicates a dataflow packet (128 or 160).
- pyproject.toml
