import os
import shutil


def copy_tree(base_dir):
    true_dir = os.path.join(base_dir, 'fixtures')
    # Make a new test dir
    fake_dir = os.path.join(base_dir, 'test_temp_dir')
    if os.path.exists(fake_dir):
        shutil.rmtree(fake_dir)
        shutil.copytree(true_dir, fake_dir)
    else:
        shutil.copytree(true_dir, fake_dir)

    return fake_dir
