![Shovels Logo](https://www.shovels.ai/theme/images/shovels-navbar-logo.svg)

# pyshovels

**pyshovels** is the unofficial Python package designed to interact with the [Shovels API](https://docs.shovels.ai/docs/introduction). 📦

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

- Python 3.9 or higher (as specified in `pyproject.toml`)
- A Shovels API key

### Installation

**For users:**

- **Install using poetry (recommended) or pip:**
  ```bash
  poetry add pyshovels
  ```
  or
  ```bash
  pip install pyshovels
  ```

**For contributors:**

- **Fork and clone the repo and install in editable mode:**
  ```bash
  git clone https://github.com/<your-username>/pyshovels.git
  cd pyshovels
  ```
  then
  ```bash
  poetry install
  ```
  or
  ```bash
  pip install -e .
  ```

**Setting your API key:**

- **Set your Shovels API key as an environment variable (recommended):**
  - Add your Shovels API key to a `.env` file - look at the [.env.example](.env.example) file for an example
  - Or set it as an environment variable directly
    ```bash
    export SHOVELS_API_KEY="your-api-key"
    ```
  - Then, load the environment variables using the `load_env` function:
    ```python
    from pyshovels import load_env, ShovelsAPI
    load_env(env_path="./path/to/.env")  # not necessary if you set the API key as an environment variable directly
    shovels = ShovelsAPI()
    ```
- **Or pass the API key as an argument to the `ShovelsAPI` class:**
  ```python
  from pyshovels import ShovelsAPI
  shovels = ShovelsAPI(api_key="your-api-key")
  ```
  > ⚠️ **Note:**
  > If passing the API key as an argument, be careful not to accidentally share it with others.

## Usage

Look at the [examples](./examples) folder for usage examples.

For more detailed examples on how to use the Shovels API, please refer to the [official documentation](https://docs.shovels.ai/api-reference/).

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a ⭐️! Thanks again!

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` file for more information.

## Contact

GitHub: [nicolasakf](https://github.com/nicolasakf)

Email: [nicolasakfonteyne@gmail.com](mailto:nicolasakfonteyn@gmail.com)
