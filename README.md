# polycom
Place and receive SIP calls with the Polycom CX300 USB phone.

Usage:
```
python polycom.py <sip username> <sip password>
```

## General Setup
Place a preferred ringtone.wav file in the root of this repository.

## Raspberry Pi Setup
Instructions to configure Raspberry Pi and install dependencies to host Polycom phone.

- Determine wpctl sink and source numbers for Polycom CX300:
```
wpctl status | grep 'Polycom CX300 Mono'
 │  *   83. Polycom CX300 Mono                  [vol: 0.40]
 │  *   84. Polycom CX300 Mono                  [vol: 1.00]
```

- Set Polycom CX300 as default source and sink:
```
wpctl set-default <listed number>
wpctl set-default <other listed number>
```

- Create a udev rule at `/etc/udev/rules.d/99-myhid.rules` containing:
```
# Polycom CX300
ATTRS{idProduct}=="9201", ATTRS{idVendor}=="095d", MODE="0660", GROUP="plugdev"
```

- Reload udev rules
```
udevadm control --reload-rules
udevadm trigger
```

- Install apt dependencies:
```
apt install libasound2-dev swig python3-dev
```

- Download pjproject source in preferred location
```
git clone https://github.com/pjsip/pjproject.git
cd pjproject
```

- Build pjproject
```
./configure CFLAGS="-fPIC"
make dep
make
```

- Build and install pjsua2
```
cd pjsip-apps/src/swig/python
make
make install
```

- Make and activate Python virtual environment in repo root
```
python -m venv --system-site-packages .venv
source .venv/bin/activate
```

- Install hidapi in venv:
```
pip install hidapi
```
