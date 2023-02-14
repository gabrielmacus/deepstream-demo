import shutil
import os
import subprocess

class CommonServices:
    @staticmethod
    def clean_tmp():
        path = '../tmp'
        shutil.rmtree(path)
        #os.system(f'rm -rf {path}')
        os.mkdir(path)