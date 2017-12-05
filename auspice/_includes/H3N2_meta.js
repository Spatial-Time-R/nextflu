var	vaccineChoice = {};
vaccineChoice['A/Sydney/5/1997'] = "1997-09-25";
vaccineChoice['A/Moscow/10/1999'] = "1999-09-25";
vaccineChoice['A/Fujian/411/2002'] = "2003-09-25";
vaccineChoice['A/California/7/2004'] = "2005-02-21";
vaccineChoice['A/Wisconsin/67/2005'] = "2006-02-21";
vaccineChoice['A/Brisbane/10/2007'] = "2007-09-25";
vaccineChoice['A/Perth/16/2009'] = "2009-09-25";
vaccineChoice['A/Victoria/361/2011'] = "2012-02-21";
vaccineChoice['A/Texas/50/2012'] = "2013-09-25";
vaccineChoice['A/Switzerland/9715293/2013'] = "2014-09-25";
vaccineChoice['A/HongKong/4801/2014'] = "2015-09-24";
vaccineChoice['A/Singapore/Infimh-16-0019/2016'] = "2017-09-28";
var vaccineStrains = Object.keys(vaccineChoice);
var branch_labels=false;
var restrictTo = {"region": "all"};

var genome_annotation = {'SP': [[1.2,1.2,1.2], [1,20,49]],
                         'HA1': [[1,1,1], [49,460,49+987]],
						 'HA2': [[1.2,1.2,1.2], [49+987,1200,1701]]};
var default_gene = 'HA1';

var structure = "5HMG.pdb"
