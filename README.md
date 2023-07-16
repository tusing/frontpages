# With Nix:

```
rm -rf cache && nix-shell --pure --command 'flask run'
```

# Without Nix:

```
pip install -r requirements.txt
rm -rf cache && flask run
```
