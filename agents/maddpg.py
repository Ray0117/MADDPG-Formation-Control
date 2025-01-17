# Adopted from https://keras.io/examples/rl/ddpg_pendulum/

import tensorflow as tf
from tensorflow.keras import layers
import numpy as np
from agents.nets.actor_network import generate_actor_network
from agents.nets.critic_network import generate_critic_network
from agents.util import * 
import tqdm

# Our basic MADDPG: Currenty assumes access to all other agents actions/policies and observations while training
# Could be interesting to explore their policy estimation and ensemble suggestions
class MADDPGAgent():
    def  __init__(
           self,
           env,
           agent_index,
           gamma=0.95,
           tau=0.01,
           critic_lr=0.002,
           actor_lr=0.001,
           noise_std_dev=0.02,
           buffer_size=10e6,
           batch_size=1024,
           ):

        self._agent_index = agent_index
        self._num_agents = len(env.observation_space)

        # With MADDPG, these are only used for the actor
        self._num_obs = env.observation_space[agent_index].shape[0]
        self._num_act = env.action_space[agent_index].shape[0]
        self._max = env.action_space[agent_index].high[0]
        self._min = env.action_space[agent_index].low[0]

        self._gamma = gamma
        self._tau = tau
        self._actor_opt = tf.keras.optimizers.Adam(actor_lr)
        self._critic_opt = tf.keras.optimizers.Adam(critic_lr)

        self._noise = OUNoise(mean=np.zeros(self._num_act), std_dev=float(noise_std_dev) * np.ones(self._num_act))
        self._actor_model = generate_actor_network(self._num_obs, self._num_act, self._max)

        # Iterate through the environment spaces to figure out the total action and obs dimensionality
        # This should work for agents with variable obs/act spaces, though this isn't the case here
        self._total_obs_size = 0
        self._total_act_size = 0
        for i in range(self._num_agents):
            if i == agent_index:
                self._obs_start_ind = self._total_obs_size
                self._act_start_ind = self._total_act_size
            self._total_obs_size += env.observation_space[i].shape[0]
            self._total_act_size += env.action_space[i].shape[0]

        self._critic_model = generate_critic_network(self._total_obs_size, self._total_act_size)

        self._target_actor = generate_actor_network(self._num_obs, self._num_act, self._max)
        self._target_critic = generate_critic_network(self._total_obs_size, self._total_act_size)

        # Making the weights equal initially
        self._target_actor.set_weights(self._actor_model.get_weights())
        self._target_critic.set_weights(self._critic_model.get_weights())

        self._actor_best = generate_actor_network(self._num_obs, self._num_act, self._max)
        self._critic_best = generate_critic_network(self._total_obs_size, self._total_act_size)

        self._actor_best_average = generate_actor_network(self._num_obs, self._num_act, self._max)
        self._critic_best_average = generate_critic_network(self._total_obs_size, self._total_act_size)

    # Sample the policy with noise from one set of the saved neural nets
    def policy(self, state, policy_param = 'last'):
        sampled_actions = None
        if(policy_param == 'last'):
            sampled_actions = tf.squeeze(self._actor_model(state))
        elif(policy_param == 'best_overall'):
            sampled_actions = tf.squeeze(self._actor_best(state))
        elif(policy_param == 'best_average'):
            sampled_actions = tf.squeeze(self._actor_best_average(state))
        else:
            sampled_actions = tf.squeeze(self._actor_model(state))
        noise = self._noise()
        # Adding noise to action
        sampled_actions = sampled_actions.numpy() + noise

        # We make sure action is within bounds
        legal_action = np.clip(sampled_actions, self._min, self._max)

        return [np.squeeze(legal_action)]

    # Noiseless action sampling
    def non_exploring_policy(self, state, policy_param = 'last'):
        sampled_actions = None
        if(policy_param == 'last'):
            sampled_actions = tf.squeeze(self._actor_model(state))
        elif(policy_param == 'best_overall'):
            sampled_actions = tf.squeeze(self._actor_best(state))
        elif(policy_param == 'best_average'):
            sampled_actions = tf.squeeze(self._actor_best_average(state))
        else:
            sampled_actions = tf.squeeze(self._actor_model(state))

        # We make sure action is within bounds
        legal_action = np.clip(sampled_actions, self._min, self._max)

        return [np.squeeze(legal_action)]

    # Custom NN updates based on the MADDPG paper
    @tf.function
    def update(
        self, state_batch, action_batch, reward_batch, next_state_batch, done_batch, next_actions
    ):
        # Split this agents states off of the blob
        local_next_state_batch = next_state_batch[:,self._obs_start_ind:self._obs_start_ind + self._num_obs]
        with tf.GradientTape() as tape:
            # Select the next action based on the next state
            target_actions = self._target_actor(local_next_state_batch, training=True)
            # Push our next actions into the blob of all of the agents next actions
            updated_next_actions = tf.concat([next_actions[:,:self._act_start_ind], target_actions[:], next_actions[:,self._act_start_ind + self._num_act:]], 1)
            # Extract this agents rewards from the reward batch
            r = tf.expand_dims(reward_batch[:,self._agent_index], -1)
            y = r + self._gamma * self._target_critic(
                [next_state_batch, updated_next_actions], training=True
            )
            critic_value = self._critic_model([state_batch, action_batch], training=True)
            # MSE of the TD error for loss
            critic_loss = tf.math.reduce_mean(tf.math.square(y - critic_value))

        # Get and apply gradients for the critic
        critic_grad = tape.gradient(critic_loss, self._critic_model.trainable_variables)
        self._critic_opt.apply_gradients(
            zip(critic_grad, self._critic_model.trainable_variables)
        )

        # Get this agents state from the blob
        local_state_batch = state_batch[:,self._obs_start_ind:self._obs_start_ind + self._num_obs]

        with tf.GradientTape() as tape:
            # Check which actions this agent would take now
            local_actions = tf.cast(self._actor_model(local_state_batch, training=True), dtype=tf.float64)
            # Stitch the actions into all of the agents actions for the critic
            updated_action = tf.concat([action_batch[:,0:self._act_start_ind], local_actions[:], action_batch[:,self._act_start_ind + self._num_act:]], 1)
            # Get the critic estimation for this set of actions
            critic_value = self._critic_model([state_batch, updated_action], training=True)
            # Use negative mean for loss since we want to do gradient ascent
            actor_loss = -tf.math.reduce_mean(critic_value)

        # Get and apply gradient for actor networks
        actor_grad = tape.gradient(actor_loss, self._actor_model.trainable_variables)
        self._actor_opt.apply_gradients(
            zip(actor_grad, self._actor_model.trainable_variables)
        )

    # This update target parameters slowly
    # Based on rate `tau`, which is much less than one.
    @tf.function
    def update_target(self, target_weights, weights):
        for (a, b) in zip(target_weights, weights):
            a.assign(b * self._tau + a * (1 - self._tau))

    # Update the networks and target networks
    def perform_update_step(self, update_batch, next_actions):
        self.update(*update_batch, next_actions)

        self.update_target(self._target_actor.variables, self._actor_model.variables)
        self.update_target(self._target_critic.variables, self._critic_model.variables)

    # Save the best average reward nets
    def cache_best_average(self):
        self._actor_best_average.set_weights(self._actor_model.get_weights())
        self._critic_best_average.set_weights(self._critic_model.get_weights())


    # Save the best overall reward nets
    def cache_best_single(self):
        self._actor_best.set_weights(self._actor_model.get_weights())
        self._critic_best.set_weights(self._critic_model.get_weights())

    # Save all of our networks
    def save_models(self, suffix=""):
        dir = "./weights/maddpg" + suffix
        self._actor_model.save_weights(dir + "/actor")
        self._critic_model.save_weights(dir + "/critic")
        self._target_actor.save_weights(dir + "/target_actor")
        self._target_critic.save_weights(dir + "/target_critic")
        self._actor_best.save_weights(dir + "/_actor_best")
        self._critic_best.save_weights(dir + "/_critic_best")
        self._actor_best_average.save_weights(dir + "/_actor_best_average")
        self._critic_best_average.save_weights(dir + "/_critic_best_average")
  
    # Load all of the networks
    def load_models(self, suffix=""):
        dir = "./weights/maddpg" + suffix
        self._actor_model.load_weights(dir + "/actor")
        self._critic_model.load_weights(dir + "/critic")
        self._target_actor.load_weights(dir + "/target_actor")
        self._target_critic.load_weights(dir + "/target_critic")
        self._actor_best.load_weights(dir + "/_actor_best")
        self._critic_best.load_weights(dir + "/_critic_best")
        self._actor_best_average.load_weights(dir + "/_actor_best_average")
        self._critic_best_average.load_weights(dir + "/_critic_best_average")
