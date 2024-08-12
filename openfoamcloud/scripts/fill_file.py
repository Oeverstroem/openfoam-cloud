import sys
import json
import os


def replace_str(file, string, replacement):
    suffix = "_tmp"
    tmp_file = file + suffix
    with open(file, "rt") as fin:
        with open(tmp_file, "wt") as fout:
            for line in fin:
                fout.write(line.replace(string, replacement))
    os.remove(file)
    os.rename(tmp_file, file)


if __name__ == "__main__":
    # total arguments
    n = len(sys.argv)

    if n != 3:
        print("Please provide the path of the config and the path of the base folder.")
        raise Exception("Not enough arguments")

    case_config_path = sys.argv[1]
    base_path = sys.argv[2]
    print("Handling case config " + case_config_path + "from base path " + base_path)

    with open(case_config_path) as f:
        case_config = json.load(f)
        for parameter_settings in case_config["parameter_settings"]:
            file_path = os.path.join(base_path, parameter_settings["path"])
            variable_escaper = "@"
            variable_name = str(parameter_settings["variable_name"])
            variable_replace = variable_escaper + variable_name + variable_escaper
            value = str(parameter_settings["value"])
            replace_str(file_path, variable_replace, value)
