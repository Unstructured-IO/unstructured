# Downloadify Example
More info available at the Github Project Page
# Downloadify Invoke Script For This Page
Downloadify.create('downloadify',{
  filename: function(){
    return document.getElementById('filename').value;
  },
  data: function(){ 
    return document.getElementById('data').value;
  },
  onComplete: function(){ 
    alert('Your File Has Been Saved!'); 
  },
  onCancel: function(){ 
    alert('You have cancelled the saving of this file.');
  },
  onError: function(){ 
    alert('You must put something in the File Contents or there will be nothing to save!'); 
  },
  swf: 'media/downloadify.swf',
  downloadImage: 'images/download.png',
  width: 100,
  height: 30,
  transparent: true,
  append: false
});