"""Metric for accuracy evaluation."""
import string
import numpy as np
from rapidfuzz.distance import Levenshtein

from mindspore import nn
import mindspore as ms


__all__ = ['RecMetric']

class RecMetric(nn.Metric):
    """
    Define accuracy metric for warpctc network.

    Args:
        ignore_space: remove space in prediction and ground truth text if True 
        filter_ood: filter out-of-dictionary characters(e.g., '$' for the default digit+en dictionary) in ground truth text. Default is True. 
        lower: convert GT text to lower case. Recommend to set True if the dictionary does not contains upper letters 

    Notes:
        Since the OOD characters are skipped during label encoding in data transformation by default, filter_ood should be True. (Paddle skipped the OOD character in label encoding and then decoded the label indices back to text string, which has no ood character.  
    """

    def __init__(self, 
            character_dict_path=None,
            ignore_space=True, 
            filter_ood=True,  
            lower=True, 
            print_flag=True, 
            **kwargs):
        super().__init__()
        self.clear()
        self.ignore_space = ignore_space
        self.filter_ood = filter_ood
        self.lower = lower
        self.print_flag = print_flag
        
        
        # TODO: use parsed dictionary object
        if character_dict_path is None:
            self.dict  = [c for c in  "0123456789abcdefghijklmnopqrstuvwxyz"]
        else:
            self.dict = []
            with open(character_dict_path, 'r') as f:
                for line in f:
                    c = line.rstrip('\n\r')
                    self.dict.append(c)

    def clear(self):
        self._correct_num = 0
        self._total_num = 0
        self.norm_edit_dis = 0.0

    def update(self, *inputs):
        """
        Updates the internal evaluation result 

        Args:
            inputs (tuple): contain two elements preds, gt
                    preds (dict): prediction output by postprocess, keys:
                        - texts, List[str], batch of predicted text strings, shape [BS, ] 
                        - confs (optional), List[float], batch of confidence values for the prediction
                    gt (tuple or list): ground truth, order defined by output_keys in eval dataloader. require element: 
                        gt_texts, for the grouth truth texts (padded to the fixed length), shape [BS, ]
                        gt_lens (optional), length of original text if padded, shape [BS, ] 
                        
        Raises:
            ValueError: If the number of the inputs is not 2.
        """
        
        if len(inputs) != 2:
            raise ValueError('Length of inputs should be 2')
        preds, gt = inputs
        
        pred_texts = preds['texts']
        #pred_confs = preds['confs']
        #print('pred: ', pred_texts, len(pred_texts))

        # remove padded chars in GT
        if isinstance(gt, tuple) or isinstance(gt, list):
            gt_texts = gt[0] # text string padded 
            gt_lens = gt[1] # text length 

            if isinstance(gt_texts, ms.Tensor):
                gt_texts = gt_texts.asnumpy()
                gt_lens = gt_lens.asnumpy()
            
            gt_texts = [gt_texts[i][:l] for i, l in enumerate(gt_lens)] 
        else:
            gt_texts = gt
        
        #print('2: ', gt_texts)
        for pred, label in zip(pred_texts, gt_texts):
            #print('pred', pred, 'END')
            #print('label ', label, 'END')

            if self.ignore_space:
                pred = pred.replace(' ', '')
                label = label.replace(' ', '')

            if self.filter_ood: # filter out of dictionary characters
                label = ''.join([c for c in label if c in self.dict]) 

            if self.lower: # convert to lower case
                label = label.lower()

            if self.print_flag:
                print(pred, " :: ", label)

            edit_distance = Levenshtein.normalized_distance(pred, label)
            self.norm_edit_dis += edit_distance 
            if pred == label:
                self._correct_num += 1
            #if edit_distance == 0:
            #    self._correct_num += 1

            self._total_num += 1

    def eval(self):
        if self._total_num == 0:
            raise RuntimeError(
                'Accuary can not be calculated, because the number of samples is 0.')
        print('correct num: ', self._correct_num,
              ', total num: ', self._total_num)
        sequence_accurancy = self._correct_num / self._total_num
        norm_edit_distance =  1 - self.norm_edit_dis / self._total_num

        return {'acc': sequence_accurancy, 'norm_edit_distance': norm_edit_distance} 

if __name__ == '__main__':
    gt = ['ba xla la!    ', 'ba       ']
    gt_len = [len('ba xla la!'), len('ba')]

    pred = ['balala', 'ba']

    m = RecMetric()
    m.update({'texts': pred}, (gt, gt_len))
    acc = m.eval()
    print(acc)
