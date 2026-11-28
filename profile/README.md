# HotWire Lab

**Zero-install browser USB hardware tools** built with **Rust + WebAssembly** (Leptos) for **Seeed Studio XIAO ESP32-S3** and **XIAO ESP32-C6**.

🌐 **Website:** [https://hotwire-lab.github.io/](https://hotwire-lab.github.io/)

## Browser Tools (Desktop Web Serial & Android WebUSB)

| Tool | Live App | Repository | Capabilities |
| :--- | :--- | :--- | :--- |
| **HotWire Bench** | [hotwire-lab.github.io/bench](https://hotwire-lab.github.io/bench/) | [`hotwire-lab/bench`](https://github.com/hotwire-lab/bench) | Mixed-signal V0.1: 2 analog + 8 digital, shared t0/trigger timebase, UART/SPI/I²C decoders, LEDC generator |
| **HotWire Logic Analyzer** | [hotwire-lab.github.io/logic](https://hotwire-lab.github.io/logic/) | [`hotwire-lab/logic`](https://github.com/hotwire-lab/logic) | 8-ch 20 MHz Logic Analyzer, Tri-State Force I/O, UART/SPI/I²C decoders, CSV/VCD |
| **HotWire Oscilloscope** | [hotwire-lab.github.io/scope](https://hotwire-lab.github.io/scope/) | [`hotwire-lab/scope`](https://github.com/hotwire-lab/scope) | 4-ch 12-bit GDMA ADC Scope (up to 1 MSPS S3 OC), FFT, Math, X-Y, Persistence |
| **HotWire SDR** | [hotwire-lab.github.io/sdr](https://hotwire-lab.github.io/sdr/) | [`hotwire-lab/sdr`](https://github.com/hotwire-lab/sdr) | 1.84–2.79 GHz RF Spectrum Analyzer, 948 MHz Wideband Scanner, Waterfall & Raw I/Q |
| **HotWire Serial Terminal** | [hotwire-lab.github.io/serial](https://hotwire-lab.github.io/serial/) | [`hotwire-lab/serial`](https://github.com/hotwire-lab/serial) | Desktop Web Serial & Android WebUSB (CDC-ACM, FTDI, CP210x, CH340, PL2303) + XIAO UART Bridge |
| **HotWire Signal Generator** | [hotwire-lab.github.io/siggen](https://hotwire-lab.github.io/siggen/) | [`hotwire-lab/siggen`](https://github.com/hotwire-lab/siggen) | Dual-ch DDS waveforms (Sine/Tri/Saw/Noise), HW LEDC Square/PWM up to 20 MHz, Sweep & 4-ch Pattern Gen |

## Shared Core & Website

* **[`hotwire-lab/hotwire-core`](https://github.com/hotwire-lab/hotwire-core)** — Shared Rust/WASM library encapsulating USB transport, zero-copy binary framing, firmware compatibility verification, `esptool-js` Web Flasher, and Leptos UI shell.
* **[`hotwire-lab/hotwire-lab.github.io`](https://github.com/hotwire-lab/hotwire-lab.github.io)** — Astro landing page for [https://hotwire-lab.github.io/](https://hotwire-lab.github.io/).

> Every tool includes a **1-click offline Demo simulator** and a built-in **`esptool-js` Web Flasher** — no drivers or desktop IDE required.

