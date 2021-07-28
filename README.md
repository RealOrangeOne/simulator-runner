# simulator-runner

Run the simulator at the push of a button

## Usage

```
pip install -r requirements.txt
mkdir output
python app.py
```

Simulations will live in the `output` directory, with `.html` and `.x3d` files with the same name in the root.

```
$ ls -1 output/
match-10070.html
match-10070.json
match-10070.mp4
...
```

On click of the "Run Simulation" button, the command defined in `$COMMAND` will be run. This can be quoted to contain arguments, but for more complex scripts, it's recommended to just write a bash script.
