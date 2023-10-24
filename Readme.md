# Krooster Dumper

A python script for logging into the "A-game" and dumping the data into [Krooster](https://www.krooster.com/)-compatible JSON files for easy updating.

## Usage

### Setup

1. Install python 3.8 or higher.
2. Install the requirements with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and change the email.

### Updating Operator Data

1. Go to [Krooster](https://www.krooster.com/).
2. Open the developer console (F12) and go to the application tab.
3. Under "Storage", click on "Local Storage" and then on "https://www.krooster.com/".
4. Right click on the "operators" value and click "Edit value" and copy the value.
5. Paste the value into `operator_list.json` and save the file.
6. Change `DUMP_OPERATORS` in `.env` to `True`.
7. Run `python dump.py`.
8. Copy the contents of `new_operator_list.json` and replace the value of "operators" in the local storage with it.


### Updating Planner/Material Data

1. Go to [Krooster Planner page](https://www.krooster.com/planner/goals).
2. Export the data by clicking on the "Export/Import Data" button.
3. Choose "Penguin-Stats" as the format and copy the data.
4. Paste the data into `planner.json` and save the file.
5. Change `DUMP_PLANNER` in `.env` to `True`.
6. Run `python dump.py`.
7. Choose "Penguin-Stats" as the format for "Import Format".
8. Copy the contents of `new_planner.json` and paste it into the "Import Data" box.
9. Click on "Import Data".


## Disclaimer

Use at your own risk. I am not responsible for any damage caused by this script.
