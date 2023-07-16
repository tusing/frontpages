# With Nix:

```
rm -rf cache && nix-shell --pure --command 'flask run --host=0.0.0.0'
```

# Without Nix:

```
pip3 install -r requirements.txt
rm -rf cache && FLASK_APP=frontpages.py flask run --host=0.0.0.0
```
