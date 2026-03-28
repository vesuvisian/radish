# CT-485 API Message Coverage Matrix

Source of truth: `docs/spec/ClimateTalk_2.0_CT-485_API_Reference_R01.pdf`

Status legend:

- `implemented`: concrete class exists and is registered
- `skeleton`: class exists with minimal payload decoding and raw payload output
- `not implemented`: not enough information present in the docs to implement

## CT-CIM Mapped Messages


| Message                                  | Request ID | Response ID | Request Class                                | Response Class                                | Status          |
| ---------------------------------------- | ---------- | ----------- | -------------------------------------------- | --------------------------------------------- | --------------- |
| Get Configuration                        | `0x01`     | `0x81`      | `GetConfigurationRequest`                    | `GetConfigurationResponse`                    | implemented     |
| Get Status                               | `0x02`     | `0x82`      | `GetStatusRequest`                           | `GetStatusResponse`                           | implemented     |
| Set Control Command                      | `0x03`     | `0x83`      | `SetControlCommandRequest`                   | `SetControlCommandResponse`                   | implemented     |
| Set Display Message                      | `0x04`     | `0x84`      | `SetDisplayMessageRequest`                   | `SetDisplayMessageResponse`                   | implemented     |
| Set Diagnostics                          | `0x05`     | `0x85`      | `SetDiagnosticsRequest`                      | `SetDiagnosticsResponse`                      | implemented     |
| Get Diagnostics                          | `0x06`     | `0x86`      | `GetDiagnosticsRequest`                      | `GetDiagnosticsResponse`                      | implemented     |
| Get Sensor Data                          | `0x07`     | `0x87`      | `GetSensorDataRequest`                       | `GetSensorDataResponse`                       | implemented     |
| Set Identification                       | `0x0D`     | `0x8D`      | `SetIdentificationRequest`                   | `SetIdentificationResponse`                   | implemented     |
| Get Identification Data                  | `0x0E`     | `0x8E`      | `GetIdentificationDataRequest`               | `GetIdentificationDataResponse`               | implemented     |
| Set Application Shared Data To Network   | `0x10`     | `0x90`      | `SetApplicationSharedDataToNetworkRequest`   | `SetApplicationSharedDataToNetworkResponse`   | implemented     |
| Get Application Shared Data From Network | `0x11`     | `0x91`      | `GetApplicationSharedDataFromNetworkRequest` | `GetApplicationSharedDataFromNetworkResponse` | implemented     |
| Set Manufacturer Device Data             | `0x12`     | `0x92`      | `SetManufacturerDeviceDataRequest`           | `SetManufacturerDeviceDataResponse`           | implemented     |
| Get Manufacturer Device Data             | `0x13`     | `0x93`      | `GetManufacturerDeviceDataRequest`           | `GetManufacturerDeviceDataResponse`           | implemented     |
| Set Network Node List                    | `0x14`     | `0x94`      | `SetNetworkNodeListRequest`                  | `SetNetworkNodeListResponse`                  | implemented     |
| Direct Memory Access Read                | `0x1D`     | `0x9D`      | `DirectMemoryAccessReadRequest`              | `DirectMemoryAccessReadResponse`              | implemented     |
| Direct Memory Access Write               | `0x1E`     | `0x9E`      | `DirectMemoryAccessWriteRequest`             | `DirectMemoryAccessWriteResponse`             | not implemented |
| Set Manufacturer Generic Data            | `0x1F`     | `0x9F`      | `SetManufacturerGenericDataRequest`          | `SetManufacturerGenericDataResponse`          | implemented     |
| Manufacturer Generic Data                | `0x20`     | `0xA0`      | `ManufacturerGenericDataRequest`             | `ManufacturerGenericDataResponse`             | implemented     |
| Manufacturer Generic Reply               | `0x21`     | `0xA1`      | `ManufacturerGenericReplyRequest`            | `ManufacturerGenericReplyResponse`            | not implemented |
| Get User Menu                            | `0x41`     | `0xC1`      | `GetUserMenuRequest`                         | `GetUserMenuResponse`                         | implemented     |
| Set User Menu Update                     | `0x42`     | `0xC2`      | `SetUserMenuUpdateRequest`                   | `SetUserMenuUpdateResponse`                   | implemented     |
| Set Factory Shared Data To Application   | `0x43`     | `0xC3`      | `SetFactorySharedDataToApplicationRequest`   | `SetFactorySharedDataToApplicationResponse`   | implemented     |
| Get Shared Data From Application         | `0x44`     | `0xC4`      | `GetSharedDataFromApplicationRequest`        | `GetSharedDataFromApplicationResponse`        | implemented     |
| Set Echo Data                            | `0x5A`     | `0xDA`      | `EchoRequest`                                | `EchoResponse`                                | implemented     |

Notes:
- `GetConfigurationResponse` (`0x81`) and `GetStatusResponse` (`0x82`) now parse MDI payloads as DB-ID datagrams (`DB_ID_TAG + DB_LENGTH + VALUE`) and report record-level details.
- Field-level semantic decoding for individual DB IDs is still incremental and profile-dependent.


## CT-485 Specific Messages


| Message                    | Request ID | Response ID | Request Class                    | Response Class                    | Status      |
| -------------------------- | ---------- | ----------- | -------------------------------- | --------------------------------- | ----------- |
| Request to Receive (R2R)   | `0x00`     | -           | `RequestToReceive`               | -                                 | implemented |
| Network State              | `0x75`     | `0xF5`      | `NetworkStateRequest`            | `NetworkStateResponse`            | implemented |
| Address Confirmation Push  | `0x76`     | `0xF6`      | `AddressConfirmationPushRequest` | `AddressConfirmationPushResponse` | implemented |
| Token Offer                | `0x77`     | `0xF7`      | `TokenOffer`                     | `TokenOfferResponse`              | implemented |
| Version Announcement       | `0x78`     | -           | `VersionAnnouncement`            | -                                 | implemented |
| Node Discovery             | `0x79`     | `0xF9`      | `NodeDiscoveryRequest`           | `NodeDiscoveryResponse`           | implemented |
| Set Address                | `0x7A`     | `0xFA`      | `SetAddressRequest`              | `SetAddressResponse`              | implemented |
| Get Node ID                | `0x7B`     | `0xFB`      | `GetNodeIdRequest`               | `GetNodeIdResponse`               | implemented |
| Network Shared Data Sector | `0x7D`     | `0xFD`      | `NetworkSharedDataSectorRequest` | `NetworkSharedDataSectorResponse` | implemented |
| Encapsulation              | `0x7E`     | `0xFE`      | `EncapsulationRequest`           | `EncapsulationResponse`           | implemented |


