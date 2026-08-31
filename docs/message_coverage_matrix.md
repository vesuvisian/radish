# CT-485 API Message Coverage Matrix (for Python decoder)

_Last validated 8/31/26_

Source of truth for message types and high-level payloads: [docs/spec/ClimateTalk_2.0_CT-485_API_Reference_R01.pdf](spec/ClimateTalk_2.0_CT-485_API_Reference_R01.pdf)
Source of truth for many lower-level payloads, such as various MDI: [docs/spec/ClimateTalk_2.0_Command_Reference_R01.pdf](spec/ClimateTalk_2.0_Command_Reference_R01.pdf)

For these tables, the IDs column presents the request and response IDs, respectively, for each message if defined. The `Parsed?` column uses the following definitions:
- `full`: concrete class exists and all payloads can be parsed
- `partial`: class exists with raw or partially implemented payload parsing
- `none`: not enough information present in the docs to implement

## CT-CIM Mapped Messages (API Reference Section 5.0)

| Message                                  | IDs           | Parsed? | Notes |
| ---------------------------------------- | ------------- | ------- | ----- |
| Get Configuration                        | `0x01`/`0x81` | partial | <sup>1</sup> |
| Get Status                               | `0x02`/`0x82` | partial | <sup>2</sup> |
| Set Control Command                      | `0x03`/`0x83` | partial | <sup>3</sup> |
| Set Display Message                      | `0x04`/`0x84` | full    |       |
| Set Diagnostics                          | `0x05`/`0x85` | full    |       |
| Get Diagnostics                          | `0x06`/`0x86` | full    |       |
| Get Sensor Data                          | `0x07`/`0x87` | partial | <sup>4</sup> |
| Set Identification                       | `0x0D`/`0x8D` | full    |       |
| Get Identification Data                  | `0x0E`/`0x8E` | full    |       |
| Set Application Shared Data To Network   | `0x10`/`0x90` | partial | Application Data not documented |
| Get Application Shared Data From Network | `0x11`/`0x91` | partial | Application Data not documented |
| Set Manufacturer Device Data             | `0x12`/`0x92` | partial | Manufacturer Device Data not documented |
| Get Manufacturer Device Data             | `0x13`/`0x93` | partial | Manufacturer Device Data not documented |
| Set Network Node List                    | `0x14`/`0x94` | full    |       |
| Direct Memory Access Read                | `0x1D`/`0x9D` | partial | Only raw payload presented in response |
| Direct Memory Access Write               | `0x1E`/`0x9E` | none    | Only mentioned in API Reference Table 68 |
| Set Manufacturer Generic Data            | `0x1F`/`0x9F` | partial | <sup>5</sup> |
| Get Manufacturer Generic Data            | `0x20`/`0xA0` | partial | <sup>5</sup> |
| Manufacturer Generic Reply               | `0x21`/`0xA1` | none    | Only mentioned in API Reference Table 68 |
| Get User Menu                            | `0x41`/`0xC1` | full    |       |
| Set User Menu Update                     | `0x42`/`0xC2` | full    |       |
| Set Factory Shared Data To Application   | `0x43`/`0xC3` | partial | Application Data not documented |
| Get Shared Data From Application         | `0x44`/`0xC4` | partial | Application Data not documented |
| Set Echo Data                            | `0x5A`/`0xDA` | full    |       |

Notes:
- <sup>1</sup> Response parsed as raw DB ID datagrams by default. The following Configuration MDI values are further parsed by node type and DB ID (Command Reference Section 7.3):
  - Furnace: `0x00`, `0x01`
  - Air Handler: `0x00`, `0x01`, `0x02` seen in logs and not yet decoded
  - Air Conditioner: `0x00`, `0x01`, `0x02`
  - Heat Pump: `0x00`, `0x01`, `0x02`
- <sup>2</sup> Response parsed as raw DB ID datagrams by default. The Following Status MDI semantic decoding are further parsed by node type and DB ID (Command Reference Section 7.4):
  - Air Handler: `0x00`, `0x01` seen in logs and not yet decoded
  - Heat Pump: `0x00`
- <sup>3</sup> Response parsed as Command Code and raw Command Data by default. The following Command Data are further parsed by Command Code (Command Reference Section 6.0), including any unknown trailing bytes:
  - `0x60`: Damper Closure Position Demand (unknown extra bytes seen)
  - `0x61` Subsystem Busy Status
  - `0x62`: Dehumidification Demand
  - `0x63`: Humidification Demand
  - `0x64`: Heat Demand
  - `0x65`: Cool Demand
  - `0x66` Fan Demand
  - `0x67`: Back-Up Heat Demand
  - `0x68`: Defrost Heat Demand
  - `0x69`: Aux / Alt Heat Demand
- <sup>4</sup> Response parsed as raw DB ID datagrams by default. The following Sensor MDI values are further parsed by node type and DB ID (Command Reference Section 7.5):
  - Furnace: `0x00`, `0x01`
  - Air Handler: `0x00`, `0x01`, `0x02` seen in logs and only partially decoded
  - Air Conditioner: `0x00`
  - Heat Pump: `0x00`
  - Crossover: `0x00`, `0x01`, `0x02`
  - Zone User Interface: `0x00`, `0x01`
  - Zone Temperature Control: `0x00`, `0x01`
  - Temperature Sensor: `0x00` (Remote Temperature)
- <sup>5</sup> Some Daikin-specific messages partially decoded
  - `0x01`: Request/response completely unknown
  - `0x02`: Request unknown; response partially decoded
  - `0x03`: Request known; response partially decoded

## CT-485 Specific Messages

| Message                    | IDs           | Parsed? | Notes |
| -------------------------- | ------------- | ------- | ----- |
| Request to Receive (R2R)   | `0x00`/-      | full    |       |
| Network State              | `0x75`/`0xF5` | full    |       |
| Address Confirmation Push  | `0x76`/`0xF6` | full    |       |
| Token Offer                | `0x77`/`0xF7` | full    |       |
| Version Announcement       | `0x78`/-      | full    |       |
| Node Discovery             | `0x79`/`0xF9` | full    |       |
| Set Address                | `0x7A`/`0xFA` | full    |       |
| Get Node ID                | `0x7B`/`0xFB` | full    |       |
| Network Shared Data Sector | `0x7D`/`0xFD` | partial | Shared data not documented |
| Encapsulation              | `0x7E`/`0xFE` | partial | Encapsulated data not documented |
