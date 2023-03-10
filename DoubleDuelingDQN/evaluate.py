#!/usr/bin/env python3

# Copyright (c) 2020, RTE (https://www.rte-france.com)
# See AUTHORS.txt
# This Source Code Form is subject to the terms of the Mozilla Public License, version 2.0.
# If a copy of the Mozilla Public License, version 2.0 was not distributed with this file,
# you can obtain one at http://mozilla.org/MPL/2.0/.
# SPDX-License-Identifier: MPL-2.0
# This file is part of L2RPN Baselines, L2RPN Baselines a repository to host baselines for l2rpn competitions.

import os
import argparse

from grid2op.MakeEnv import make
from grid2op.Runner import Runner
from grid2op.Reward import *
from grid2op.Action import *

from l2rpn_baselines.DoubleDuelingDQN.doubleDuelingDQN import DoubleDuelingDQN as D3QNAgent
from l2rpn_baselines.DoubleDuelingDQN.doubleDuelingDQNConfig import DoubleDuelingDQNConfig as D3QNConfig
from l2rpn_baselines.utils.save_log_gif import save_log_gif

DEFAULT_LOGS_DIR = "./logs-evals"
DEFAULT_NB_EPISODE = 10
DEFAULT_NB_PROCESS = 1
DEFAULT_MAX_STEPS = -1
DEFAULT_NUM_FRAMES = 4
DEFAULT_VERBOSE = True


def cli():
    parser = argparse.ArgumentParser(description="Eval baseline DDDQN")
    parser.add_argument("--data_dir", default="rte_case14_realistic",
                        help="Path to the dataset root directory")
    parser.add_argument("--load_file", required=True,
                        help="The path to the model [.h5]")
    parser.add_argument("--logs_dir", required=False,
                        default=DEFAULT_LOGS_DIR, type=str,
                        help="Path to output logs directory")
    parser.add_argument("--nb_episode", required=False,
                        default=DEFAULT_NB_EPISODE, type=int,
                        help="Number of episodes to evaluate")
    parser.add_argument("--nb_process", required=False,
                        default=DEFAULT_NB_PROCESS, type=int,
                        help="Number of cores to use")
    parser.add_argument("--max_steps", required=False,
                        default=DEFAULT_MAX_STEPS, type=int,
                        help="Maximum number of steps per scenario")
    parser.add_argument("--gif", action='store_true',
                        help="Enable GIF Output")
    parser.add_argument("--verbose", action='store_true',
                        help="Verbose runner output")
    parser.add_argument("--num_frames", required=False,
                        default=DEFAULT_NUM_FRAMES, type=int,
                        help="Number of stacked states")
    return parser.parse_args()


def evaluate(env,
             load_path=None,
             logs_path=DEFAULT_LOGS_DIR,
             nb_episode=DEFAULT_NB_EPISODE,
             nb_process=DEFAULT_NB_PROCESS,
             max_steps=DEFAULT_MAX_STEPS,
             num_frames=DEFAULT_NUM_FRAMES,
             verbose=DEFAULT_VERBOSE,
             is_quantizated=False,
             save_gif=True):

    import tensorflow as tf  # lazy import to save import time
    
    # Set config
    D3QNConfig.N_FRAMES = num_frames
    D3QNConfig.VERBOSE = verbose
    
    # Limit gpu usage
    physical_devices = tf.config.list_physical_devices('GPU')
    if len(physical_devices):
        tf.config.experimental.set_memory_growth(physical_devices[0], True)

    runner_params = env.get_params_for_runner()
    runner_params["verbose"] = verbose

    # Create agent
    agent = D3QNAgent(env.observation_space,
                      env.action_space,
                      is_training=False,
                      is_quantizated=is_quantizated)

    # Load weights from file
    agent.load(load_path)

    # Build runner
    runner = Runner(**runner_params,
                    agentClass=None,
                    agentInstance=agent)

    # Print model summary
    if verbose:
        stringlist = []
        agent.Qmain.model.summary(print_fn=lambda x: stringlist.append(x))
        short_model_summary = "\n".join(stringlist)
        print(short_model_summary)

    # Run
    os.makedirs(logs_path, exist_ok=True)
    res = runner.run(path_save=logs_path,
                     nb_episode=nb_episode,
                     nb_process=nb_process,
                     max_iter=max_steps,
                     pbar=verbose)

    print(1)
    # Print summary
    if verbose:
        print("Evaluation summary:")
        for _, chron_name, cum_reward, nb_time_step, max_ts in res:
            msg_tmp = "chronics at: {}".format(chron_name)
            msg_tmp += "\ttotal reward: {:.6f}".format(cum_reward)
            msg_tmp += "\ttime steps: {:.0f}/{:.0f}".format(nb_time_step,
                                                            max_ts)
            print(msg_tmp)

    if save_gif:
        save_log_gif(logs_path, res)

    return agent,res

if __name__ == "__main__":
    # Parse command line
    args = cli()
    # Create dataset env
    env = make(args.data_dir,
               reward_class=RedispReward,
               action_class=TopologyChangeAndDispatchAction,
               other_rewards={
                   "bridge": BridgeReward,
                   "overflow": CloseToOverflowReward,
                   "distance": DistanceReward
               })
    # Call evaluation interface
    evaluate(env,
             load_path=args.load_file,
             logs_path=args.logs_dir,
             nb_episode=args.nb_episode,
             nb_process=args.nb_process,
             max_steps=args.max_steps,
             num_frames=args.num_frames,
             verbose=args.verbose,
             save_gif=args.gif)
