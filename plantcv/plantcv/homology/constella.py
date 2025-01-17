import numpy as np
import matplotlib.pyplot as plt
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.cluster.hierarchy import cut_tree
from plantcv.plantcv import params


def _get_empty_count(cur_index_id):
    """Helper function for getting empty count"""
    empty_count = 0
    for i in cur_index_id:
        if i is None:
            empty_count += 1
    return empty_count


def _get_empty_indicies(cur_index, cur_plms_copy):
    """Helper function for getting empty indicies"""
    empty_index = []
    for i, v in zip(cur_index, cur_plms_copy.iloc[cur_index, 0].values):
        if v is None:
            empty_index.append(i)
    return empty_index


def _get_unique_ids(cur_index_id):
    """Helper function for getting id's"""
    unique_ids = []
    for id_ in cur_index_id:
        if id_ is not None and id_ not in unique_ids:
            unique_ids.append(id_)
    return unique_ids


def _get_rogues(cur_plms_copy):
    """Helper function for getting rogues"""
    rogues = []
    for i, x in enumerate(cur_plms_copy['group'].values):
        if x is None:
            rogues.append(i)
    return rogues


def _generate_labelnames(plmnames, grpnames):
    """Helper function for generating label names"""
    labelnames = []
    for li in range(0, len(plmnames)):
        labelname = f'{plmnames[li]} ({grpnames[li]})'
        labelnames.append(labelname)
    return labelnames


def _pair_unnassigned(unique_ids, cur_index, cur_index_id, cur_plms_copy, empty_count, sanity_check_pos):
    """Helper function for pairing unassigned"""
    for uid in unique_ids:
        # If only one plm assigned a name in current cluster and a second unnamed plm exists
        # transfer ID over to create a pair
        if np.count_nonzero(np.array(cur_index_id) == uid) < 2 and empty_count == 1:
            # Store boolean positions for plms with IDs matching current id out of current cluster
            match_ids = [i for i, x in enumerate(cur_plms_copy.iloc[cur_index, 0].values == uid) if x]
            # Store boolean positions for plms which are unnamed out of current cluster
            null_ids = []
            for i, x in enumerate(cur_plms_copy.iloc[cur_index, 0].values):
                if x is None:
                    null_ids.append(i)
            # If exactly 1 matching ID and 1 null ID (i.e. 2 plms total)
            # continue to pass ID name to the unnamed plm
            if len(match_ids) + len(null_ids) == 2:
                # Sanity check! Pairs must be on different days
                pair_names = cur_plms_copy.iloc[[cur_index[i] for i in match_ids + null_ids], 1].values
                if pair_names[0].split('_')[sanity_check_pos] != pair_names[1].split('_')[sanity_check_pos]:
                    # Transfer identities to the unnamed plm
                    cur_plms_copy.iloc[[cur_index[i] for i in null_ids], 0] = uid


def constella(cur_plms, pc_starscape, group_iter, outfile_prefix):
    """
    Group pseudo-landmarks into homology groupings

    Inputs:
    cur_plms       = A pandas array of plm multivariate space representing capturing two adjacent frames in a
                     time series or otherwise analogous dataset in order to enable homology assignments
    pc_starscape   = PCA results from starscape
    group_iter     = Group ID counter
    outfile_prefix = User defined file path and prefix name for PCA output graphics

    :param cur_plms: pandas.core.frame.DataFrame
    :param pc_starscape: pandas.core.frame.DataFrame
    :param group_iter: int
    :param outfile_prefix: str
    """
    # Copy dataframe to avoid modifying the input dataframe
    cur_plms_copy = cur_plms.copy(deep=True)

    sanity_check_pos = 2  # Needs to point at days in image identifier!

    singleton_no = pc_starscape.shape[0]

    if params.debug is not None:
        print(f'{singleton_no} plms to group')

    plm_links = linkage(pc_starscape.loc[:, pc_starscape.columns[2:len(pc_starscape.columns)]].values, 'ward')

    # For n-1 to 2 leaves on the current hierarchical cluster dendrogram...
    for c in np.arange(singleton_no - 1, 2, -1):
        # Extract current number of clusters for the agglomeration step
        cutree = cut_tree(plm_links, n_clusters=c)
        # Generate a list of all current clusters identified
        group_list = np.unique(cutree)

        # For the current cluster being queried...
        for g in group_list:
            # Create list of current clusters row indices in pandas dataframe
            cur_index = [i for i, x in enumerate(cutree == g) if x]
            # Create list of current clusters present group identity assignments
            cur_index_id = np.array(cur_plms_copy.iloc[cur_index, 0])
            # Are any of the plms in the current cluster unnamed, how many?
            empty_count = _get_empty_count(cur_index_id)
            empty_index = _get_empty_indicies(cur_index, cur_plms_copy)
            # Are any of the plms in the current cluster already assigned an identity, what are those identities?
            unique_ids = _get_unique_ids(cur_index_id)
            # If cluster is two unnamed plms exactly, assign this group their own identity as a pair
            if empty_count == 2:
                pair_names = cur_plms_copy.iloc[empty_index, 1].values
                # Sanity check! Pairs must be on different days
                if pair_names[0].split('_')[sanity_check_pos] != pair_names[1].split('_')[sanity_check_pos]:
                    cur_plms_copy.iloc[empty_index, 0] = group_iter
                    group_iter = group_iter + 1
                else:
                    cur_plms_copy.iloc[empty_index[0], 0] = group_iter
                    cur_plms_copy.iloc[empty_index[1], 0] = group_iter + 1
                    group_iter = group_iter + 2
            # If cluster is one unnamed plm and one plm with an identity, assign the unnamed plm the identity of the
            _pair_unnassigned(unique_ids, cur_index, cur_index_id, cur_plms_copy, empty_count, sanity_check_pos)
    rogues = _get_rogues(cur_plms_copy)
    for rogue in rogues:
        cur_plms_copy.iloc[[rogue], 0] = group_iter
        group_iter = group_iter + 1

    grpnames = cur_plms_copy.loc[:, ['group']].values
    plmnames = cur_plms_copy.loc[:, ['plmname']].values

    labelnames = _generate_labelnames(plmnames, grpnames)

    if params.debug is not None:
        plt.figure()
        plt.title('')
        plt.xlabel('')
        plt.ylabel('')
        dendrogram(plm_links, color_threshold=100, orientation="left", leaf_font_size=10, labels=np.array(labelnames))
        plt.tight_layout()

        if params.debug == "print":
            plt.savefig(outfile_prefix + '_plmHCA.png')
            plt.close()
        elif params.debug == "plot":
            plt.show()

    return cur_plms_copy, group_iter
