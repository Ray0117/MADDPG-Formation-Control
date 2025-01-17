# MADDPG-Formation-Control
## Installing the project

To install this projects dependencies, run

```req
pip install -r requirements.txt
```

Our project is dependent on OpenAI's Multi-agent Particle Environment with installation instructions [here](https://github.com/openai/multiagent-particle-envs).

The environment used is out of date, so in order to run it, the changes detailed [here](https://github.com/openai/multiagent-particle-envs/pull/54) must be made in the library.

The required modifications are in the file 
\maddpg-formation-control\src\multiagent\multiagent\multi_discrete.py"

Comment out gym.spaces import prng in line 7,  
and change line 33 from  

```
random_array = prng.np_random.rand(self.num_discrete_space)  
```
to  
```
random_array = np.random.RandomState().rand(self.num_discrete_space)
```

If you encounter the following error  
```
ImportError: cannot import name 'reraise' from 'gym.utils'
```
Open maddpg-formation-control\src\multiagent\multiagent\rendering.py and comment out from gym.utils import reraise in line 14,  
change line 20 from  
```
 reraise(suffix="HINT: you can install pyglet directly via 'pip install pyglet'. But if you really just want to install all Gym dependencies and not have to think about it, 'pip install -e .[all]' or 'pip install gym[all]' will do it.")
 ```
 to  
 ```
 raise ImportError("HINT: you can install pyglet directly via 'pip install pyglet'. But if you really just want to install all Gym dependencies and not have to think about it, 'pip install -e .[all]' or 'pip install gym[all]' will do it.")
 ```
 and line 25 from  
 ```
 reraise(prefix="Error occured while running `from pyglet.gl import *`",suffix="HINT: make sure you have OpenGL install. On Ubuntu, you can run 'apt-get install python-opengl'. If you're running on a server, you may need a virtual frame buffer; something like this should work: 'xvfb-run -s \"-screen 0 1400x900x24\" python <your_script.py>'")
 ```
 to  
 ```
 raise ImportError("Error occured while running `from pyglet.gl import *")
```


It is also likely that you will encounter the following error
```
AttributeError: 'ImageData' object has no attribute 'data'
```
if you do, change the file \maddpg-formation-control\src\multiagent\multiagent\rendering.py" in line 101 from
```
arr = np.fromstring(image_data.data, dtype=np.uint8, sep='')
```
to
```
arr = np.fromstring(image_data.get_data(), dtype=np.uint8, sep='')
```

## Training the Agents
We define two different training scripts depending on whether we want to train a centralized or decentralized agent.


### Centralized Agents
To train a centralized DDPG agent for 1000 episodes in a formation control with collision avoidance scenario, you can run the following command


```central
python centralized_experiment.py
```

Further control over the experiments can be gained through use of the command line options, defined as


```central-opt
usage: centralized_experiment.py [-h] [--scenario SCENARIO_NAME] [--num_eps NUM_EPS] [--save_images IMAGES] [--save_models SAVE_MODEL] [--load_models LOAD_MODEL] [--train TRAIN]
                                 [--save_suffix SAVE_SUFFIX] [--load_suffix LOAD_SUFFIX]

File to run experiments for som scenario with a centralized agent.

optional arguments:
  -h, --help            show this help message and exit
  --scenario SCENARIO_NAME
                        Name of the scenario we want to run: formation_w_coll_avoidance, formation_w_goal or simple_formation
  --num_eps NUM_EPS     Number of episodes to train for.
  --save_images IMAGES  True to save images and gifs, anything else not to.
  --save_models SAVE_MODEL
                        True to save models, anything else not to.
  --load_models LOAD_MODEL
                        True to load models, anything else not to.
  --train TRAIN         True to train models, anything else not to.
  --save_suffix SAVE_SUFFIX
                        Suffix for saving the file.
  --load_suffix LOAD_SUFFIX
                        Suffix for loading the file.
```

### Decentralized Agents
To train a set of MADDPG agents for 1000 episodes in a formation control with collision avoidance scenario, you can run the following command


```decentral
python decentralized_experiment.py
```

Further customization of the experiment and the agents are available through the options

```decentral opt
usage: decentralized_experiment.py [-h] [--agent AGENT] [--scenario SCENARIO_NAME] [--num_eps NUM_EPS] [--save_images IMAGES] [--save_models SAVE_MODEL] [--load_models LOAD_MODEL]
                                   [--train TRAIN] [--save_suffix SAVE_SUFFIX] [--load_suffix LOAD_SUFFIX]

File to run experiments for som scenario with a centralized agent.

optional arguments:
  -h, --help            show this help message and exit
  --agent AGENT         Name of the agent types: Valid values are 'decddpg' and 'maddpg'
  --scenario SCENARIO_NAME
                        Name of the scenario we want to run: simple_formation or formation_w_goal or formation_w_coll_avoidance
  --num_eps NUM_EPS     Number of episodes to train for.
  --save_images IMAGES  True to save images and gifs, False not to.
  --save_models SAVE_MODEL
                        True to save models, False not to.
  --load_models LOAD_MODEL
                        True to load models, anything not to.
  --train TRAIN         True to train models, anything else not to.
  --save_suffix SAVE_SUFFIX
                        Suffix for saving the file
  --load_suffix LOAD_SUFFIX
                        Suffix for loading the file
```

## Evaluating an Agent

To evaluate either agent after training, simply set the save\_images option for either script to 'True'. For an example, with the decentralized agent


```decentral
python decentralized_experiment.py --save_images True
```

Alternatively, if you wish to evaluate an agent with saved agent models, one can load the agents given the loading suffix, if one was used when saving the agents, and by setting the training option to false. For example

```decentral
python decentralized_experiment.py --save_images True --load_models True --load_suffix <SUFFIX-USED-WHEN-SAVING-MODEL> --train False
```

## Results
Below, we include the training curves for the different agents on the formation control with collision avoidance and a goal scenario.

![alt text](img/training_data.png "Training Curves")

Find the images for the behavioural analysis of the MADDPG agents below.


![alt text](img/info_average_2_1.png "MADDPG Particle Trajectories")
![alt text](img/info_average_2_2.png "MADDPG Formation Error")
![alt text](img/info_average_2_3.png "MADDPG Formation Goal Distance")
