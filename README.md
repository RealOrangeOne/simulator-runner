# simulator runner

Run the simulator at the push of a button

[![CI](https://github.com/RealOrangeOne/simulator-runner/actions/workflows/ci.yml/badge.svg)](https://github.com/RealOrangeOne/simulator-runner/actions/workflows/ci.yml)

## Usage

```
pip install -r requirements.txt
python app.py
```

Simulations will live in the `output` directory, with `.html` and `.x3d` files with the same name. The logs will be in a `logs.txt` file. The directory name will be a modified ISO format, although anything which parses to a date is supported.

```
.
├── output
│   └── 2021-08-07T19_20_46.108422
│       ├── 2021-08-07T18_31_56.html
│       ├── 2021-08-07T18_31_56.json
│       ├── 2021-08-07T18_31_56.x3d
│       └── logs.txt
└── zone-0
    ├── crane.py
    └── forklift.py
```

On click of the "Run Simulation" button, the command defined in `$COMMAND` will be run. This can be quoted to contain arguments, but for more complex scripts, it's recommended to just write a bash script.
