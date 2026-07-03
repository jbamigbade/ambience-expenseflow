from google.adk.cli.fast_api import get_fast_api_app
app = get_fast_api_app(agents_dir='.', web=True)
print("Registered routes in get_fast_api_app:")
for route in app.routes:
    print(f"{route.path} -> {route.name}")
