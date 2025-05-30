# # Agencies to Scrape:
Utah - Bogm
Utah - Dogm
Divison of oil gas and mining

Bureau of oil gas and mining

filter out all the cases that relate to indian tribal authority stuff

which ones are for permits that are still in the approval process

which ones are the biggest in terms of GHG impacts

Did a bunch of browsing and figured out that
https://oilgas.ogm.utah.gov/oilgasweb/live-data-search/lds-files/files-lu.xhtml

probably seems to be the best bet for sourced data.

Use the date function and select files between dates like so:
01/01/2025,01/02/2025

Bad news, it does require you to go ahead and only search in intervals of 256

But it does let you use the tab system to get them all?




So to start off with this should have a function that takes in these 2 dates and returns all files. Once they are finished.


Here is the system for selecting files and potential dates.


```html
<form id="srchCForm" name="srchCForm" method="post" action="/oilgasweb/live-data-search/lds-files/files-lu.xhtml;jsessionid=5724E00D12BABBDF0D8502D7EC1ACFF2" enctype="application/x-www-form-urlencoded" onsubmit="return false;">
<input type="hidden" name="srchCForm" value="srchCForm">
<input type="hidden" name="javax.faces.ViewState" id="j_id1:javax.faces.ViewState:1" value="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" autocomplete="off">
<input id="srchCForm:companyStr" type="hidden" name="srchCForm:companyStr"><input id="srchCForm:isLoggedInStr" type="hidden" name="srchCForm:isLoggedInStr">
					<!-- Toolbar -->
					<br><div id="srchCForm:j_idt70" class="ui-toolbar ui-widget ui-widget-header ui-corner-all ui-helper-clearfix" role="toolbar" style="width: 800px; height: 32px;"><div class="ui-toolbar-group-left"><table border="0" cellpadding="1" cellspacing="2">
<tbody>
<tr>
<td><label for="srchCForm:srchCCheckboxMenu">Choose Search Criteria:&nbsp;</label></td>
<td><div id="srchCForm:srchCCheckboxMenu" class="ui-selectcheckboxmenu ui-widget ui-state-default ui-corner-all" style="width:252px;"><div class="ui-helper-hidden-accessible"><input id="srchCForm:srchCCheckboxMenu_focus" name="srchCForm:srchCCheckboxMenu_focus" type="text" readonly="readonly" aria-expanded="false" aria-labelledby="srchCForm:srchCCheckboxMenu_label"></div><div class="ui-helper-hidden"><input id="srchCForm:srchCCheckboxMenu:0" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="wellId" data-escaped="true" checked="checked" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:0">API Well Number</label><input id="srchCForm:srchCCheckboxMenu:1" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="oprName" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:1">Operator</label><input id="srchCForm:srchCCheckboxMenu:2" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="cntyName" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:2">County Name</label><input id="srchCForm:srchCCheckboxMenu:3" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="fldName" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:3">Field Name</label><input id="srchCForm:srchCCheckboxMenu:4" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="section" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:4">Section</label><input id="srchCForm:srchCCheckboxMenu:5" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="twspRng" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:5">Location (Twn-Rng)</label><input id="srchCForm:srchCCheckboxMenu:6" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="wellName" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:6">Well Name</label><input id="srchCForm:srchCCheckboxMenu:7" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="wellTypeDescr" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:7">Well Type</label><input id="srchCForm:srchCCheckboxMenu:8" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="wellStatusDescr" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:8">Well Status</label><input id="srchCForm:srchCCheckboxMenu:9" name="srchCForm:srchCCheckboxMenu" type="checkbox" value="modifyDate" data-escaped="true" onchange="executeOnChange()"><label for="srchCForm:srchCCheckboxMenu:9">Modify Date</label></div><span class="ui-selectcheckboxmenu-label-container"><label class="ui-selectcheckboxmenu-label ui-corner-all" id="srchCForm:srchCCheckboxMenu_label">Selection</label></span><div class="ui-selectcheckboxmenu-trigger ui-state-default ui-corner-right"><span class="ui-icon ui-icon-triangle-1-s"></span></div></div></td>
<td><script id="srchCForm:j_idt74" type="text/javascript">executeOnHide = function() {PrimeFaces.ab({s:"srchCForm:j_idt74",f:"srchCForm",u:"srchCForm:srchCPnlGrp",pa:arguments[0]});}</script></td>
<td><script id="srchCForm:j_idt75" type="text/javascript">executeOnChange = function() {PrimeFaces.ab({s:"srchCForm:j_idt75",f:"srchCForm",u:"srchCForm:srchCPnlGrp",pa:arguments[0]});}</script></td>
</tr>
</tbody>
</table>
</div><div class="ui-toolbar-group-right"><table border="0" cellpadding="1" cellspacing="2">
<tbody>
<tr>
<td><button id="srchCForm:j_idt77" name="srchCForm:j_idt77" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left" onclick="PF('readDlgId').show();" type="button" role="button" aria-disabled="false"><span class="ui-button-icon-left ui-icon ui-c ui-icon-comment"></span><span class="ui-button-text ui-c">Read</span></button></td>
<td><div id="srchCForm:j_idt78" class="ui-dialog ui-widget ui-widget-content ui-corner-all ui-shadow ui-hidden-container ui-draggable ui-resizable" style="width: auto; height: auto;" role="dialog" aria-labelledby="srchCForm:j_idt78_title" aria-hidden="true"><div class="ui-dialog-titlebar ui-widget-header ui-helper-clearfix ui-corner-top ui-draggable-handle"><span id="srchCForm:j_idt78_title" class="ui-dialog-title">Instructions</span><a href="#" class="ui-dialog-titlebar-icon ui-dialog-titlebar-close ui-corner-all" aria-label="Close" role="button"><span class="ui-icon ui-icon-closethick"></span></a></div><div class="ui-dialog-content ui-widget-content" style="height: 150px;">Use comma delimiters for more than one value. Only use alphabetical characters, numbers and commas.<br><br>Examples:<br><br>API Well Number: 4300130001,4300130003,4300130030<br>Operator: Bridger,Husky<br>County: Grand,Elder,Lake<br>Field Name: Wildcat,Rozel,Buttes<br></div><div class="ui-resizable-handle ui-resizable-n" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-s" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-e" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-w" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-ne" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-nw" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-se ui-icon ui-icon-gripsmall-diagonal-se" style="z-index: 90;"></div><div class="ui-resizable-handle ui-resizable-sw" style="z-index: 90;"></div></div></td>
<td>
								<!-- &lt;span class="ui-separator"&gt;&lt;span
									class="ui-icon ui-icon-grip-dotted-vertical" /&gt;&lt;/span&gt;
								&lt;h:outputText
									style="font-style: italic;vertical-align: text-top;"
									value="Exporters: " /&gt;
								&lt;span class="ui-separator"&gt;&lt;span
									class="ui-icon ui-icon-grip-dotted-vertical" /&gt;&lt;/span&gt;
								&lt;h:outputText
									style="font-style: italic;vertical-align: text-top;"
									value="Page Only" /&gt;
								&lt;h:commandLink&gt;
									&lt;h:graphicImage library="img" style="border:0"
										name="csv.png.xhtml.png" width="24" /&gt;
									&lt;p:dataExporter type="csv"
										target="dataTableForm:srchRsltDataTable"
										fileName="well_file" pageOnly="true" /&gt;
								&lt;/h:commandLink&gt;
								&lt;span class="ui-separator"&gt;&lt;span
									class="ui-icon ui-icon-grip-dotted-vertical" /&gt;&lt;/span&gt;
								&lt;h:outputText
									style="font-style: italic;vertical-align: text-top;"
									value="All Pages" /&gt;
								&lt;h:commandLink&gt;
									&lt;h:graphicImage library="img" style="border:0"
										name="csv.png.xhtml.png" width="24" /&gt;
									&lt;p:dataExporter type="csv"
										target="dataTableForm:srchRsltDataTable"
										fileName="well_file_all" pageOnly="false" /&gt;
								&lt;/h:commandLink&gt; --></td>
</tr>
</tbody>
</table>
</div></div>
					<!-- End of Toolbar -->
					
					<!-- Search Criteria Panel Group --><span id="srchCForm:srchCPnlGrp">
						<!-- API Well Number Panel --><div id="srchCForm:wellIdPnl" class="ui-panel ui-widget ui-widget-content ui-corner-all" style="margin-top: 1px;        margin-bottom: 1px;        margin-left: 0px;        margin-right: 0px;        width: 800px;" data-widget="widget_srchCForm_wellIdPnl"><div id="srchCForm:wellIdPnl_content" class="ui-panel-content ui-widget-content"><table id="srchCForm:j_idt94" class="ui-panelgrid ui-widget" role="grid"><tbody><tr class="ui-widget-content ui-panelgrid-even" role="row"><td role="gridcell" class="ui-panelgrid-cell" style="font-weight: bold; width: 170px;"><label for="srchCForm:wellIdCompOpr">API Well Number:</label></td><td role="gridcell" class="ui-panelgrid-cell" style="width: 90px;">
											<!-- &lt;f:selectItem itemLabel="Select One" itemValue="" noSelectionOption="true" /&gt; --><select id="srchCForm:wellIdCompOpr" name="srchCForm:wellIdCompOpr" size="1">	<option value="LIKE" selected="selected">LIKE</option>
	<option value="EQUALS">EQUALS</option>
	<option value="BETWEEN">BETWEEN</option>
</select><div id="srchCForm:j_idt103" aria-live="polite" class="ui-message"></div></td><td role="gridcell" class="ui-panelgrid-cell" style="width: 190px;"><input id="srchCForm:wellIdInput" name="srchCForm:wellIdInput" type="text" size="32" onfocus="moveCursorToEnd(this)" class="ui-inputfield ui-inputtext ui-widget ui-state-default ui-corner-all" role="textbox" aria-disabled="false" aria-readonly="false"><div id="srchCForm:j_idt105" aria-live="polite" class="ui-message"></div></td><td role="gridcell" class="ui-panelgrid-cell" style="width: 88px;"><button id="srchCForm:wellIdClearBtn" name="srchCForm:wellIdClearBtn" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left" onclick="PrimeFaces.ab({s:&quot;srchCForm:wellIdClearBtn&quot;,u:&quot;srchCForm:wellIdCompOpr srchCForm:wellIdInput&quot;,g:false,pa:[{name:&quot;todo&quot;,value:&quot;clearBtn&quot;}]});return false;" type="submit" role="button" aria-disabled="false"><span class="ui-button-icon-left ui-icon ui-c ui-icon-trash"></span><span class="ui-button-text ui-c">Clear</span></button></td><td role="gridcell" class="ui-panelgrid-cell" style="width: 88px;"><button id="srchCForm:wellIdCloseBtn" name="srchCForm:wellIdCloseBtn" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left" onclick="PrimeFaces.ab({s:&quot;srchCForm:wellIdCloseBtn&quot;,u:&quot;srchCForm:wellIdPnl&quot;,g:false,pa:[{name:&quot;todo&quot;,value:&quot;closeBtn&quot;}]});return false;" type="submit" role="button" aria-disabled="false"><span class="ui-button-icon-left ui-icon ui-c ui-icon-closethick"></span><span class="ui-button-text ui-c">Close</span></button></td></tr></tbody></table></div></div>
						<!-- Operator Name Panel -->
						<!-- County Name Panel -->
						<!-- Field Name Panel -->
						<!-- Location (Twn-Rng) -->
						<!-- Section Panel -->
						<!-- Well Name Panel -->
						<!-- Well Type Panel -->
						<!-- Well Status Panel -->
						<!-- Modify Date --><span id="srchCForm:focusId"></span><script type="text/javascript">$(function(){PrimeFaces.focus('srchCForm:wellIdInput');});</script>
						<!-- Search Button Panel --><div id="srchCForm:srchPnl" class="ui-panel ui-widget ui-widget-content ui-corner-all" style="margin-top: 1px;        margin-bottom: 1px;        margin-left: 0px;        margin-right: 0px;        width: 800px;" data-widget="widget_srchCForm_srchPnl"><div id="srchCForm:srchPnl_content" class="ui-panel-content ui-widget-content"><table id="srchCForm:j_idt264" class="ui-panelgrid ui-widget" role="grid"><tbody><tr class="ui-widget-content ui-panelgrid-even" role="row"><td role="gridcell" class="ui-panelgrid-cell" style="width: 100%;"><button id="srchCForm:srchBtn" name="srchCForm:srchBtn" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left" onclick="PrimeFaces.ab({s:&quot;srchCForm:srchBtn&quot;,u:&quot;srchCForm&quot;});return false;" type="submit" role="button" aria-disabled="false"><span class="ui-button-icon-left ui-icon ui-c ui-icon-search"></span><span class="ui-button-text ui-c">Search</span></button>&nbsp;
										<button id="srchCForm:clearAllBtn" name="srchCForm:clearAllBtn" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left" onclick="PrimeFaces.ab({s:&quot;srchCForm:clearAllBtn&quot;,u:&quot;srchCForm:srchCPnlGrp&quot;,g:false,pa:[{name:&quot;todo&quot;,value:&quot;clearAllBtn&quot;}]});return false;" type="submit" role="button" aria-disabled="false"><span class="ui-button-icon-left ui-icon ui-c ui-icon-trash"></span><span class="ui-button-text ui-c">Clear All</span></button>&nbsp;
										<button id="srchCForm:resetBtn" name="srchCForm:resetBtn" class="ui-button ui-widget ui-state-default ui-corner-all ui-button-text-icon-left" onclick="PrimeFaces.ab({s:&quot;srchCForm:resetBtn&quot;,u:&quot;dataTableForm:srchRsltDataTable&quot;,g:false,pa:[{name:&quot;todo&quot;,value:&quot;resetBtn&quot;}]});return false;" type="submit" role="button" aria-disabled="false"><span class="ui-button-icon-left ui-icon ui-c ui-icon-arrowrefresh-1-s"></span><span class="ui-button-text ui-c">Reset</span></button></td></tr></tbody></table></div></div></span>
					<br>
					<!-- End of Search Criteria Panel Group -->
</form>
```


