from pyshovels import ShovelsAPI, load_env

if __name__ == "__main__":
    load_env(env_path="./path/to/.env")
    shovels = ShovelsAPI()
    response = shovels.search_location(
        query="NY",
        level="states"
    )
    print(response)
