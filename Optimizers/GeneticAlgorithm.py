import numpy as np
import os
import math
from ..ProcessData import seq2oh,oh2seq,saveseq,GetCharMap
import random

class GeneticAthm():
    def __init__(self,
                 Generator,
                 Predictor,
                 z_dim=64):
        self.z_dim = z_dim
        self.x = np.random.normal(size=(3200,z_dim))
        self.Generator = Generator
        try:
            self.Seqs = self.Generator(self.x)
            if type(self.Seqs) is not list or type(self.Seqs[0]) is not str:
                print("GeneratorError: Output of Generator(x) Must be a list of str")
                raise
            self.charmap,self.invcharmap = GetCharMap(self.Seqs)
            self.oh = seq2oh(self.Seqs,self.charmap)
        except:
            print("GeneratorError: Generator(x) can't run")
            raise
            
        self.Predictor = Predictor
        try:
            self.Score = self.Predictor(self.Seqs)
            if type(self.Score) is not np.ndarray:
                print("PredictorError: Output of Predictor(Generator(x)) must be a numpy.ndarray")
                raise
            elif  len(self.Score.shape) != 1 or self.Score.shape[0] != len(self.Seqs):
                print("PredictorError: Except shape of Predictor(Generator(x)) is ({},) but got a {}".format(len(self.Seqs),str(self.Score.shape)))
                raise
        except:
            print("PredictorError: Predictor(Generator(x)) can't run")
            raise
            
    def run(self,
            outdir='./EAresult',
            MaxPoolsize=20000,
            P_rep=0.3,
            P_new=0.25,
            P_elite=0.25,
            MaxIter=5000):
        self.outdir = outdir
        if os.path.exists(self.outdir) == False:
            os.makedirs(self.outdir)
        self.MaxPoolsize = MaxPoolsize
        self.P_rep = P_rep
        self.P_new = P_new
        self.P_elite = P_elite
        self.MaxIter = MaxIter
        I = np.argsort(self.Score)
        I = I[::-1]
        self.Score = self.Score[I]
        self.x = self.x[I,:]
        self.oh = self.oh[I,:,:]
        for iteration in range(1,1+self.MaxIter):
            Poolsize = self.Score.shape[0]
            Nnew = math.ceil(Poolsize*self.P_new)
            Nelite = math.ceil(Poolsize*self.P_elite)
            IParent = self.select_parent( Nnew, Nelite, Poolsize) #从精英和普通中各挑一半作为母代
            Parent = self.x[IParent,:].copy()
            #生成新序列
            x_new = self.act(Parent)#生成子代隐空间
            oh_new = seq2oh(self.Generator(x_new),self.charmap)
            Score_new = self.Predictor(self.Generator(x_new))
            self.x = np.concatenate([self.x, x_new])
            self.oh = np.concatenate([self.oh, oh_new])
            self.Score = np.append(self.Score,Score_new)
            I = np.argsort(self.Score)
            I = I[::-1]#将序列池按分数降序排列
            self.x = self.x[I,:]
            self.oh = self.oh[I,:,:]
            self.Score = self.Score[I]
            #去掉表现差的序列
            I = self.delRep(self.oh ,P_rep)
            self.x = np.delete(self.x,I,axis=0)
            self.oh  = np.delete(self.oh ,I,axis=0)
            self.Score = np.delete(self.Score,I,axis=0)
            self.x = self.x[:MaxPoolsize, :]
            self.oh = self.oh[:MaxPoolsize, :, :]
            self.Score = self.Score[:MaxPoolsize]
            print('Iter = ' + str(iteration) + ' , BestScore = ' + str(self.Score[0]))
            if iteration%100 == 0:
                np.save(outdir+'/ExpIter'+str(iteration),self.Score)
                Seq = oh2seq(self.oh,self.invcharmap)
                np.save(outdir+'/latentv'+str(iteration),self.x)
                saveseq(outdir+'/SeqIter'+str(iteration)+'.fa',Seq)
                print('Iter {} was saved!'.format(iteration))
        return
    
    def PMutate(self, z): #单点突变
        p = np.random.randint(0,z.shape[0])
        z[p] = np.random.normal()
        return
    
    def Reorganize(self, z, Parent): #随机重组
        index = np.random.randint(0, 1,size=(z.shape[0]))
        j = np.random.randint(0, Parent.shape[0])
        for i in range(z.shape[0]):
            if index[i] == 1:
                z[i] = Parent[j,i].copy()
        return
    
    def select_parent(self,Nnew, Nelite, Poolsize):
        ParentFromElite = min(Nelite,Nnew//2)
        ParentFromNormal = min(Poolsize-Nelite, Nnew-ParentFromElite)
        I_e = random.sample([ i for i in range(Nelite)], ParentFromElite)
        I_n = random.sample([ i+Nelite for i in range(Poolsize - Nelite)], ParentFromNormal)
        I = I_e + I_n
        return I

    def act(self, Parent):
        for i in range(Parent.shape[0]):
            action = np.random.randint(0,1)
            if action == 0:
                self.PMutate(Parent[i,:])
            elif action == 1:
                self.Reorganize(Parent[i,:], Parent)
        return Parent
    
    def delRep(self, Onehot, p):
        I = []
        n = Onehot.shape[0]
        i = 0
        while i < n-1:
            if i not in I:
                for j in range(i+1,n):
                    if j in I: continue
                    if np.sum(Onehot[i,:,:] != Onehot[j,:,:]) / (Onehot.shape[1]*2) < p:
                        I.append(j)
            i += 1
        return I
