function notepad_click(adnl_address){ 
	if (document.getElementById(adnl_address).style.display == "block") { 
		document.getElementById(adnl_address).style.display = "none";
	}
	else {
		document.getElementById(adnl_address).style.display = "block";
		document.getElementById(adnl_address).style.left = (event.pageX + 15) + "px";
		document.getElementById(adnl_address).style.top = (event.pageY + 15) + "px";
	}
};
