# radish

Radish interfaces with Daikin / ClimateTalk-style HVAC networks over CT-485 (RS-485).

It includes:

- ESPHome profiles for sniffing bus traffic and publishing it to MQTT
- Python tooling to decode and inspect live MQTT frames
- An ESPHome external component for on-device protocol handling and optional AutoNet join

## Documentation

Full setup guides, status, specs, and references:

**https://vesuvisian.com/radish/**

Source for the site lives under [`docs/`](docs/). Start with [`docs/index.md`](docs/index.md) for the getting-started path (hardware → flash → decode → optional AutoNet).

### Local Documentation

To view the docs locally, run:

```bash
pip install -r docs/requirements.txt
mkdocs serve
```

Then open the provided URL (usually `http://127.0.0.1:8000/radish`).
