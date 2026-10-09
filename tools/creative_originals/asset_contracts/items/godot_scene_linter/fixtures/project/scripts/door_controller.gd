extends Node3D
## Opens the door when its timer fires.

signal opened


func open() -> void:
	opened.emit()
