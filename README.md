# Ampero 2 Firmware Reverse Engineering

Reverse engineering the Hotone Ampero II guitar processor firmware (MIMXRT1052 Cortex-M7) and its Flutter-based editor software.

## Project Overview

| Component | Details |
|-----------|---------|
| **Target Hardware** | Hotone Ampero II (i.MX RT1052 Cortex-M7 @ 600MHz) |
| **Firmware Location** | `/home/maico/Programming/ampero2/` |
| **Editor Software** | `/home/maico/Programming/ampero2/Ampero II/` (Flutter/Dart) |
| **Analysis Tools** | Ghidra 12.2, REA MCP, custom Python scripts |

## Firmware Files

```
ampero2/
├── section0_mainapp.elf    # Main application at flash 0x60010000 (primary analysis target)
├── firmware.elf            # Full firmware at 0x08000000 (bootloader + app)
├── section3_resources.bin  # 6.7MB raw 16-bit signed audio (impulse responses)
├── algorithm.json          # 2.5MB effect definitions (17 modules, ~450 effects)
└── extract_modules.py      # Module extraction script
```

### Memory Map (i.MX RT1052)
| Region | Address Range | Purpose |
|--------|---------------|---------|
| Flash | 0x60000000 - 0x6FFFFFFF | Main firmware storage |
| RAM | 0x20000000 - 0x203FFFFF | SDRAM (4MB) |
| ITCM | 0x00000000 - 0x000FFFFF | Instruction TCM |
| DTCM | 0x20000000 - 0x200FFFFF | Data TCM |

## Key Findings

### 1. Effect Definition Tables (section0_mainapp.elf @ 0x60187d00)

Tables mapping effect codes to function pointers, matching `algorithm.json`:

```c
// AMP module (Index 3)
{ 0x03000000, ptr_0x010ee180 },
{ 0x03010100, ptr_0x2d0ce180 },
{ 0x03010000, ptr_0x4d0ce180 },
{ 0x03020100, ptr_0x6d0ce180 },
{ 0x03020000, ptr_0x390ee180 },
{ 0x03030100, ptr_0x99fce280 },
{ 0x03030000, ... },

// DYN module (Index 2)  
{ 0x020d0300, ... },
{ 0x020e0300, ... },
```

**Mystery**: Function pointers show 0x20000000 (512MB) increments - likely RAM relocation addresses or XOR-encoded.

### 2. Signal Chain Processing

- **DlgEffectChain.c** string at `0x6004c3ef` (also `0x80381bf` in firmware.elf)
- Preceding jump table with Thumb-2 STR instructions (`0x9002`, `0x9003`, etc.)
- Function `FUN_6004c438` accesses `DAT_6004c680`, manipulates `param_2 >> 6`
- Shared memory region at `0x600c0000` (4KB)

### 3. Vector Tables

**section0_mainapp.elf** (relative offsets from base 0x60010000):
```
0x000:  0x00000547    // Initial SP
0x004:  0x0000054B    // Reset → 0x6001054B (Thumb entry)
0x008:  0x0000054F    // NMI
0x00C:  0x00000553    // HardFault
...
```

**firmware.elf** (absolute addresses at 0x08000000):
- Reset handler at `0x08001000` (recognized as `entry` function)

### 4. Module System References

| String | Address | Context |
|--------|---------|---------|
| `SLOT_NUM` | 0x60017ebd | `"SourceSlot < SLOT_NUM"` |
| `SLOT_ALGRO` | 0x6003017a | `"== SLOT_ALGRO"` |
| `GetAlgroNumAMP` | 0x60061afc | `"Num < GetAlgroNumAMP()"` |
| `SetCABRelation` | 0x6002fb42 | `"SetCABRelation"` |
| `GROUP_NUM_DYN` | 0x60062e34 | `"GROUP_NUM_DYN"` |
| `Chain == 1` | 0x60022a97 | Chain selection logic |
| `Chain A` | 0x60242709 | Chain identifier |

### 5. Effect Modules (from algorithm.json)

17 modules, ~450 effects total:

| Index | Module | Effects | Prefix |
|-------|--------|---------|--------|
| 0 | CATCH | 8 | 0x00xxxxxx |
| 1 | FREQ | 12 | 0x01xxxxxx |
| 2 | DYN | 35 | 0x02xxxxxx |
| 3 | AMP | 85 | 0x03xxxxxx |
| 4 | WAH | 18 | 0x04xxxxxx |
| 5 | DRV | 42 | 0x05xxxxxx |
| 6 | EQ | 28 | 0x06xxxxxx |
| 7 | FX | 55 | 0x07xxxxxx |
| 8 | CAB | 24 | 0x08xxxxxx |
| 9 | MOD | 68 | 0x09xxxxxx |
| 10 | DLY | 32 | 0x0Axxxxxx |
| 11 | RVB | 28 | 0x0Bxxxxxx |
| 12 | VOL | 8 | 0x0Cxxxxxx |
| 13 | IR | 16 | 0x0Dxxxxxx |
| 14 | PREAMP | 12 | 0x0Exxxxxx |
| 15 | SEND | 4 | 0x0Fxxxxxx |
| 16 | RETURN | 4 | 0x10xxxxxx |

### 6. Resources (section3_resources.bin)

- **6.7MB raw 16-bit signed PCM audio**
- Impulse responses for cabinet simulation
- No headers, contiguous audio chunks
- Format: 48kHz mono (typical for IR)

### 7. Flutter Editor (Ampero II/app.so)

**Dart AOT compiled (x86_64, 11.5MB):**
- `EffectChainWidget`, `EffectChainProvider`, `EffectChainLineWidget`
- Preset cloud APIs: `https://community.hotoneaudio.com.cn/api/v1/preset/...`
- USB Audio / MIDI routing
- Backup/Restore functionality
- OTA firmware update logic

**Flutter Kernel** (kernel_blob.bin, 75MB): Contains Dart intermediate representation

### 8. Audio Driver Paths (firmware.elf)

| Path | Address Range | Purpose |
|------|---------------|---------|
| DynamicInterface | 0x08000000+ | Dynamic effect processing |
| PresetInterface | 0x08000000+ | Preset management |
| GlobalInterface | 0x08000000+ | Global settings |
| SplitNode | 0x08000000+ | Signal routing |
| InputSource | 0x08000000+ | Audio input handling |

## Analysis Tools & Scripts

### REA MCP Commands Used
```bash
# Open binaries
rea open_binary section0_mainapp.elf
rea open_binary firmware.elf

# Search strings
rea search_strings "DlgEffectChain" --document section0_mainapp.elf
rea search_strings "SLOT_NUM" --document section0_mainapp.elf

# List procedures
rea list_procedures --document section0_mainapp.elf
rea list_procedures --document firmware.elf

# Examine memory
rea read_bytes --address 0x60187d00 --length 256 --document section0_mainapp.elf
rea inspect_address_context --address 0x6004c3ef --document section0_mainapp.elf
```

### Python Scripts
```python
# extract_modules.py - Extract module catalog from algorithm.json
import json
with open('algorithm.json') as f:
    data = json.load(f)
for module in data['PluginProperties']['Modules']['Catalog']:
    print(f"{module['Name']} Index={module['Index']} Effects={len(module['Alg'])}")
```

## Next Steps

- [ ] **Decode effect table function pointers** - Test XOR keys, check RAM mapping
- [ ] **Disassemble signal chain jump table** - Full analysis of 0x6004c3e0 area
- [ ] **Trace audio processing pipeline** - DynamicInterface, PresetInterface in firmware.elf
- [ ] **Analyze kernel_blob.bin** - Flutter kernel for additional app logic
- [ ] **Map effect codes to implementations** - Cross-reference algorithm.json with firmware
- [ ] **Document IR format** - Parse section3_resources.bin structure
- [ ] **Build effect parameter map** - Link editor UI to firmware parameters

## References

- [i.MX RT1052 Reference Manual](https://www.nxp.com/docs/en/reference-manual/IMXRT1050RM.pdf)
- [ARM Cortex-M7 Technical Reference](https://developer.arm.com/documentation/ddi0646/latest)
- [Ghidra 12.2](https://ghidra-sre.org/)
- [REA MCP](https://github.com/ret2labs/rea)

---

*Generated from reverse engineering session. Last updated: 2026-10-26*