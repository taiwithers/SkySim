# Movie

## Configuration TOML

```{literalinclude} ../../../examples/movie.toml
```

## Command and Output

Assuming the above TOML file (available in the [examples
directory](https://github.com/taiwithers/SkySim/tree/main/examples)) has been
saved in the current directory as
`movie.toml`, you can then run `poetry run skysim movie.toml`,
which produces the below video.

```{raw} html
<video controls src="../_static/examples/movie.mp4" width=800 height=800></video>
```
