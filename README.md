# One-Shot Traffic Assignment with Forward-Looking Penalization


<img src="https://i.ibb.co/4JdNT9z/METIS.png" alt="METIS" border="0" width="300" height="200">

Authors: Giuliano Cornacchia, Mirco Nanni, and Luca Pappalardo.

Pre-print available [here](https://arxiv.org/abs/2306.13704).

In this repository you can find the Python code to replicate the analysis of our work regarding METIS: a cooperative, one-shot Traffic Asssignment (TA) algorithm that combines alternative routing with edge penalization and informed route scoring to assign routes to trip to reduce total CO2.

We uso SUMO to simulate the impact of the routes generated by METIS (as well as several baselines) using the mobility simulator SUMO. You can find details on how to install SUMO in this readme file.

__

```
Cornacchia, Giuliano, Mirco Nanni, and Luca Pappalardo.
One-Shot Traffic Assignment with Forward-Looking Penalization.
arXiv preprint arXiv:2306.13704 (2023).
```

If you use the code in this repository, please cite our paper:

```
@misc{cornacchia2023oneshot,
      title={One-Shot Traffic Assignment with Forward-Looking Penalization}, 
      author={Giuliano Cornacchia and Mirco Nanni and Luca Pappalardo},
      year={2023},
      eprint={2306.13704},
      archivePrefix={arXiv},
      primaryClass={cs.MA}
}
```

## Abstract

Traffic assignment (TA) is crucial in optimizing transportation systems and consists in efficiently assigning routes to a collection of trips. Existing TA algorithms often do not adequately consider real-time traffic conditions, resulting in inefficient route assignments. This paper introduces METIS, a cooperative, one-shot TA algorithm that combines alternative routing with edge penalization and informed route scoring. We conduct experiments in several cities to evaluate the performance of METIS against state-of-the-art one-shot methods. Compared to the best baseline, METIS significantly reduces CO2 emissions by 18% in Milan, 28\% in Florence, and 46% in Rome, improving trip distribution considerably while still having low computational time. Our study proposes METIS as a promising solution for optimizing TA and urban transportation systems. 


## Usage



## Setup

## How to install and configure SUMO (Simulation of Urban MObility) 🚗🚙🛻

### Install SUMO

Please always refer to the [SUMO Installation page](https://sumo.dlr.de/docs/Installing/index.html)
for the latest installation instructions.

#### > Windows

To install SUMO on Windows it is necessary to download the installer [here](https://sumo.dlr.de/docs/Downloads.php#windows) and run the executable.

#### > Linux

To install SUMO on Linux is it necessary to execute the following commands:

```
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-doc
```

#### > macOS

SUMO can be installed on macOS via [Homebrew](https://brew.sh/).

You can install and update Homebrew as following:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
brew update
brew install --cask xquartz
```
To install SUMO:
```
brew tap dlr-ts/sumo
brew install sumo
```


### Configure SUMO

After installing SUMO you must configure your `PATH` and `SUMO_HOME` environment variables.

Suppose you installed SUMO at `/your/path/to/sumo-<version>`

#### > Windows
1. On the Windows search box search for "Edit the system environment variables" option and open it;
2. Under user variables select `PATH` and click Edit. If no such variable exists you must create it with the New-Button; 
3. Append `;/your/path/to/sumo-<version>/bin` to the end of the `PATH` value (do not delete the existing values);
4. Under user variables select `SUMO_HOME` and click Edit. If no such variable exists you must create it with the New-Button;
5. Set `/your/path/to/sumo-<version>` as the value of the `SUMO_HOME` variable.

#### > Linux

1. Open a file explorer and go to `/home/YOUR_NAME/`;
2. Open the file named `.bashrc` with a text editor;
3. Place this code export `SUMO_HOME="/your/path/to/sumo-<version>/"` somewhere in the file and save;
4. Reboot your computer.


#### > macOS

First you need to determine which shell (bash or zsh) you are currently working with. In a terminal, `type ps -p $$`.

##### ZSH

In a Terminal, execute the following steps:

1. Run the command `open ~/.zshrc`, this will open the `.zshrc` file in TextEdit;
2. Add the following line to that document: `export SUMO_HOME="/your/path/to/sumo-<version>"` and save it;
3. Apply the changes by entering: `source ~/.zshrc`.

##### bash

In a Terminal, execute the following steps:

1. Run the command `open ~/.bash_profile`, this will open the `.bash_profile` file in TextEdit;
2. Add the following line to that document: `export SUMO_HOME="/your/path/to/sumo-<version>"` and save it;
3. Apply the changes by entering: `source ~/.bash_profile`.
