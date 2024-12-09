import os
import re
import threading
import time
import fnmatch
from queue import Queue
import tkinter as tk
from tkinter import PhotoImage
from tkinter import filedialog, messagebox
from tkinter.ttk import Treeview
from PIL import Image, ImageTk  # For handling and displaying thumbnails

class ImageTaggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("El Caption")
        
        icon_path = os.path.join(os.path.dirname(__file__), "elCaption.png")
        self.root.iconphoto(False, PhotoImage(file=icon_path))

        # Background saving variables
        self.save_queue = Queue()
        self.save_thread = threading.Thread(target=self.process_save_queue, daemon=True)
        self.save_thread.start()

        # Other variables
        self.directory = ""
        self.images = []
        self.current_image_index = -1
        self.all_tags = set()
        self.image_tags = {}
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # UI Elements
        self.create_ui()
        
    def process_save_queue(self):
        """Background thread to handle file saves."""
        while True:
            item = self.save_queue.get()  # Get the next file to save
            if item == (None, None):  # Exit signal
                print("Exiting save thread...")
                self.save_queue.task_done()
                break

            image_name, tags = item
            if image_name is not None and tags is not None:  # Ensure valid data
                try:
                    tag_file = os.path.splitext(image_name)[0] + ".txt"
                    tag_path = os.path.join(self.directory, tag_file)

                    # Write tags to the file
                    with open(tag_path, "w") as f:
                        f.write(", ".join(tags))
                except Exception as e:
                    print(f"Error saving file {image_name}: {e}")

            self.save_queue.task_done()  # Mark task as complete
            time.sleep(0.1)  # Slight delay to avoid overloading resources

    def parse_filter_query(self, query):
        """Parse the filter query and return a list of matching image names."""
        filtered_images = []

        # Preprocess query
        query = query.strip()
        include_tags = []
        exclude_tags = []

        # Handle NOT conditions first
        not_matches = re.findall(r"!\(([^)]+)\)", query)
        exclude_tags = [tag.strip() for tag in not_matches]
        query = re.sub(r"!\([^)]+\)", "", query)

        # Handle OR conditions
        if "OR" in query:
            or_tags = [tag.strip() for tag in query.split("OR") if tag.strip()]
            for image_name, tags in self.image_tags.items():
                if any(tag in tags for tag in or_tags):
                    filtered_images.append(image_name)
        else:
            # Handle AND conditions (comma-separated or remaining tags)
            include_tags = [tag.strip() for tag in query.split(",") if tag.strip()]
            for image_name, tags in self.image_tags.items():
                # Match inclusion and exclusion conditions
                if all(any(fnmatch.fnmatch(t, pattern) for t in tags) for pattern in include_tags) and not any(
                    any(fnmatch.fnmatch(t, pattern) for t in tags) for pattern in exclude_tags
                ):
                    filtered_images.append(image_name)

        return filtered_images


    def apply_filter(self):
        """Apply the filter and update the image grid."""
        query = self.filter_entry.get().strip()
        if not query:
            # If query is empty, reset to show all images
            self.display_thumbnails(self.images)
            return

        # Get filtered images
        filtered_images = self.parse_filter_query(query)

        # Update the grid with filtered images
        self.display_thumbnails(filtered_images)


    
    def create_ui(self):
        # Directory selection
        self.dir_frame = tk.Frame(self.root)
        self.dir_frame.pack(fill=tk.X, padx=5, pady=5)

        self.dir_label = tk.Label(self.dir_frame, text="Selected Directory:")
        self.dir_label.pack(side=tk.LEFT)

        self.dir_path = tk.Entry(self.dir_frame, width=50)
        self.dir_path.pack(side=tk.LEFT, padx=5)

        self.dir_button = tk.Button(self.dir_frame, text="Browse", command=self.select_directory)
        self.dir_button.pack(side=tk.LEFT, padx=5)

        self.process_button = tk.Button(self.dir_frame, text="Process Images and Tags", command=self.process_directory)
        self.process_button.pack(side=tk.LEFT, padx=5)

        # Main layout (panes)
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Images Pane (Fixed width)
        self.images_frame = tk.Frame(self.main_pane, width=320)
        self.main_pane.add(self.images_frame)

        # Images Label (Top of the Pane)
        self.images_label = tk.Label(self.images_frame, text="Images", anchor="w")
        self.images_label.pack(fill=tk.X, padx=5, pady=2)

        # Filter Section
        self.filter_frame = tk.Frame(self.images_frame)
        self.filter_frame.pack(fill=tk.X, padx=5, pady=2)

        self.filter_label = tk.Label(self.filter_frame, text="Filter:")
        self.filter_label.pack(side=tk.LEFT)

        self.filter_button = tk.Button(self.filter_frame, text="Apply", command=self.apply_filter)
        self.filter_button.pack(side=tk.RIGHT)

        self.filter_entry = tk.Entry(self.images_frame, width=40)
        self.filter_entry.pack(fill=tk.X, padx=5, pady=2)
        self.filter_entry.bind("<Return>", lambda event: self.apply_filter())

        # Images Grid
        self.images_canvas = tk.Canvas(self.images_frame, width=300)
        self.images_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.images_scroll = tk.Scrollbar(self.images_frame, orient="vertical", command=self.images_canvas.yview)
        self.images_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.images_canvas.configure(yscrollcommand=self.images_scroll.set)
        self.images_inner_frame = tk.Frame(self.images_canvas, width=300)
        self.images_canvas.create_window((0, 0), window=self.images_inner_frame, anchor="nw")
        self.images_inner_frame.bind("<Configure>", lambda e: self.images_canvas.configure(scrollregion=self.images_canvas.bbox("all")))

        # Right panes: Selected image and tags
        self.right_pane = tk.PanedWindow(self.main_pane, orient=tk.HORIZONTAL)
        self.main_pane.add(self.right_pane)

        # Selected image
        self.image_frame = tk.Frame(self.right_pane)
        self.right_pane.add(self.image_frame, minsize=300)

        self.image_label = tk.Label(self.image_frame, text="Selected Image")
        self.image_label.pack()

        self.image_display = tk.Label(self.image_frame, bg="gray")
        self.image_display.pack(fill=tk.BOTH, expand=True)

        # Tags section
        self.tags_pane = tk.PanedWindow(self.right_pane, orient=tk.HORIZONTAL)
        self.right_pane.add(self.tags_pane, minsize=200)

        # Image-specific tags
        self.image_tags_frame = tk.Frame(self.tags_pane)
        self.tags_pane.add(self.image_tags_frame, minsize=150)

        self.image_tags_label = tk.Label(self.image_tags_frame, text="Image Tags")
        self.image_tags_label.pack()

        self.image_tags_list = tk.Listbox(self.image_tags_frame)
        self.image_tags_list.pack(fill=tk.BOTH, expand=True)
        self.image_tags_list.bind("<Double-1>", self.remove_tag_from_image)

        # All tags
        self.all_tags_frame = tk.Frame(self.tags_pane)
        self.tags_pane.add(self.all_tags_frame, minsize=150)

        self.all_tags_label = tk.Label(self.all_tags_frame, text="All Tags")
        self.all_tags_label.pack()

        # All Tags Filter
        self.all_tags_filter_frame = tk.Frame(self.all_tags_frame)
        self.all_tags_filter_frame.pack(fill=tk.X, padx=5, pady=2)

        self.all_tags_filter_entry = tk.Entry(self.all_tags_filter_frame, width=40)
        self.all_tags_filter_entry.pack(fill=tk.X, padx=5)
        self.all_tags_filter_entry.bind("<KeyRelease>", self.update_all_tags_filter)

        self.all_tags_list = tk.Listbox(self.all_tags_frame)
        self.all_tags_list.pack(fill=tk.BOTH, expand=True)
        self.all_tags_list.bind("<Double-1>", self.add_tag_to_current_image)
        self.all_tags_list.bind("<<ListboxSelect>>", self.find_tag_in_image_tags)
        
        # Create a context menu for the All Tags list
        self.all_tags_menu = tk.Menu(self.all_tags_list, tearoff=0)
        self.all_tags_menu.add_command(label="Rename", command=self.rename_tag)
        self.all_tags_menu.add_command(label="Delete", command=self.delete_tag)
        self.all_tags_menu.add_command(label="Filter", command=self.filter_by_tag)  # Add Filter option

        # Bind the right-click event to show the context menu
        self.all_tags_list.bind("<Button-3>", self.show_all_tags_menu)  # For Windows/Linux
        self.all_tags_list.bind("<Button-2>", self.show_all_tags_menu)  # For macOS
        
        # Add Tag Section (below Image Tags List)
        self.add_tag_frame = tk.Frame(self.image_tags_frame)
        self.add_tag_frame.pack(fill=tk.X, padx=5, pady=5)

        self.add_tag_entry = tk.Entry(self.add_tag_frame, width=20)
        self.add_tag_entry.pack(side=tk.LEFT, padx=5)

        self.add_tag_button = tk.Button(self.add_tag_frame, text="Add Tag", command=self.add_new_tag)
        self.add_tag_button.pack(side=tk.LEFT)
        
    def filter_by_tag(self):
        """Filter images by the selected tag."""
        selection = self.all_tags_list.curselection()
        if not selection:
            return

        # Get the selected tag
        selected_tag = self.all_tags_list.get(selection[0])

        # Update the filter entry with the selected tag and apply the filter
        self.filter_entry.delete(0, tk.END)
        self.filter_entry.insert(0, selected_tag)
        self.apply_filter()
        
    def add_new_tag(self):
        """Add a new tag to the selected image and update All Tags."""
        if self.current_image_index == -1:
            messagebox.showwarning("No Image Selected", "Please select an image before adding a tag.")
            return

        # Get the new tag from the entry field
        new_tag = self.add_tag_entry.get().strip()
        if not new_tag:
            messagebox.showwarning("Empty Tag", "Tag cannot be empty.")
            return

        image_name = self.images[self.current_image_index]

        # Check if the tag already exists for the image
        if new_tag in self.image_tags[image_name]:
            messagebox.showinfo("Tag Exists", f"The tag '{new_tag}' already exists for this image.")
            return

        # Add the tag to the image
        self.image_tags[image_name].append(new_tag)

        # Update the All Tags list
        if new_tag not in self.all_tags:
            self.all_tags.add(new_tag)

            # Add the new tag in alphabetical order
            index = sorted(self.all_tags, key=self.natural_sort_key).index(new_tag)
            self.all_tags_list.insert(index, new_tag)

        # Highlight the tag in All Tags if it belongs to the current image
        self.update_all_tags_highlight()

        # Update the Image Tags list
        self.image_tags_list.insert(tk.END, new_tag)

        # Clear the entry field
        self.add_tag_entry.delete(0, tk.END)

        # Save the changes
        self.queue_file_save(image_name)

        print(f"Added tag: {new_tag} to image: {image_name}")


    def update_all_tags_filter(self, event=None):
        """Filter the All Tags list based on the text in the filter entry."""
        if event and event.widget != self.all_tags_filter_entry:
            return  # Ignore events from other widgets

        query = self.all_tags_filter_entry.get().strip().lower()
        self.all_tags_list.delete(0, tk.END)

        for tag in sorted(self.all_tags, key=self.natural_sort_key):
            if query in tag.lower():
                self.all_tags_list.insert(tk.END, tag)

        # Reapply highlight to the tags in the current image
        self.update_all_tags_highlight()


        
    def show_all_tags_menu(self, event):
        """Show context menu for All Tags on right-click."""
        try:
            index = self.all_tags_list.nearest(event.y)
            self.all_tags_list.selection_clear(0, tk.END)
            self.all_tags_list.selection_set(index)
            self.all_tags_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"Error showing context menu: {e}")

    def delete_tag(self):
        """Delete a tag from all images and All Tags."""
        selection = self.all_tags_list.curselection()
        if not selection:
            return

        tag_to_delete = self.all_tags_list.get(selection[0])

        # Confirm deletion
        confirm = messagebox.askyesno("Delete Tag", f"Are you sure you want to delete '{tag_to_delete}' from all images?")
        if not confirm:
            return

        # Preserve current scroll position and selection
        scroll_position = self.all_tags_list.yview()
        selected_index = self.all_tags_list.curselection()

        # Remove the tag from all images and queue for saving
        images_to_save = []
        for image_name, tags in self.image_tags.items():
            if tag_to_delete in tags:
                tags.remove(tag_to_delete)
                images_to_save.append(image_name)

        # Remove the tag from All Tags
        if tag_to_delete in self.all_tags:
            self.all_tags.remove(tag_to_delete)

        # Update UI
        self.update_ui()

        # Restore the scroll position and selection
        self.all_tags_list.yview_moveto(scroll_position[0])
        if selected_index:
            self.all_tags_list.selection_set(selected_index[0])

        # Queue file operations in the background
        threading.Thread(target=self.queue_deletion_operations, args=(images_to_save, tag_to_delete)).start()

        print(f"Deleted tag: {tag_to_delete}")

    def queue_deletion_operations(self, images_to_save, tag_to_delete):
        """Handle file updates for deletions in the background."""
        for image_name in images_to_save:
            self.queue_file_save(image_name)

        print(f"Completed deletion operations for tag: {tag_to_delete}")

    
    def rename_tag(self):
        """Rename a tag across all images."""
        selection = self.all_tags_list.curselection()
        if not selection:
            return

        old_tag = self.all_tags_list.get(selection[0])

        # Prompt for the new tag name
        new_tag = tk.simpledialog.askstring("Rename Tag", f"Rename '{old_tag}' to:")
        if not new_tag or new_tag.strip() == old_tag:
            return  # Do nothing if no new name is provided or name hasn't changed
        new_tag = new_tag.strip()

        # Preserve current scroll position and selection
        scroll_position = self.all_tags_list.yview()
        selected_index = self.all_tags_list.curselection()

        images_to_save = set()  # Track images that need saving
        new_all_tags = set(self.all_tags)  # Copy current tags

        # Update tags across all images
        for image_name, tags in self.image_tags.items():
            if old_tag in tags:
                tags.remove(old_tag)
                if new_tag not in tags:  # Avoid duplicates
                    tags.append(new_tag)
                images_to_save.add(image_name)

        # Update All Tags
        new_all_tags.discard(old_tag)
        new_all_tags.add(new_tag)
        self.all_tags = new_all_tags

        # Update UI
        self.update_ui()

        # Restore scroll position and selection
        self.all_tags_list.yview_moveto(scroll_position[0])
        if selected_index:
            self.all_tags_list.selection_set(selected_index[0])

        # Queue updated images for saving
        for image_name in images_to_save:
            self.queue_file_save(image_name)

        print(f"Renamed tag '{old_tag}' to '{new_tag}'. Updated {len(images_to_save)} images.")




    def _on_mouse_wheel(self, event):
        scroll_units = int(event.delta / 120) or int(event.delta / 10)  # Adjust for macOS
        self.images_canvas.yview_scroll(-scroll_units, "units")


    def _on_mouse_wheel_linux(self, event):
        """Scroll the canvas vertically on Linux."""
        if event.num == 4:  # Scroll up
            self.images_canvas.yview_scroll(-1, "units")
        elif event.num == 5:  # Scroll down
            self.images_canvas.yview_scroll(1, "units")


    def display_thumbnails(self, image_list=None):
        """Display thumbnails for a given list of images (default to all images)."""
        if image_list is None:
            image_list = self.images

        # Clear existing thumbnails
        for widget in self.images_inner_frame.winfo_children():
            widget.destroy()

        # Thumbnail size and padding
        thumbnail_size = 50
        padding = 10

        for index, image_name in enumerate(image_list):
            # Truncate the image name
            if len(image_name) > 15:
                display_name = f"{image_name[:3]}...{image_name[-12:]}"
            else:
                display_name = image_name

            # Load and resize thumbnail
            img_path = os.path.join(self.directory, image_name)
            img = Image.open(img_path)
            img.thumbnail((thumbnail_size, thumbnail_size))  # Resize to thumbnail size
            img_tk = ImageTk.PhotoImage(img)

            # Create image button
            btn = tk.Button(
                self.images_inner_frame,
                image=img_tk,
                text=display_name,
                compound="top",
                command=lambda i=self.images.index(image_name): self.select_image_by_index(i),
            )
            btn.image = img_tk  # Keep a reference to avoid garbage collection
            btn.grid(row=index // 2, column=index % 2, padx=padding, pady=padding)

    def select_image_by_index(self, index):
        """Handle selection of an image by its index."""
        self.current_image_index = index
        image_name = self.images[index]

        # Display the selected image
        img_path = os.path.join(self.directory, image_name)
        self.display_selected_image(img_path)

        # Update tags list
        self.image_tags_list.delete(0, tk.END)
        for tag in self.image_tags[image_name]:  # Keep the original order
            self.image_tags_list.insert(tk.END, tag)

        # Update highlights in the All Tags list
        self.update_all_tags_highlight()

    
    def select_directory(self):
        """Open a file dialog to select a directory."""
        self.directory = filedialog.askdirectory()
        self.dir_path.delete(0, tk.END)
        self.dir_path.insert(0, self.directory)
        
    @staticmethod
    def natural_sort_key(s):
        """Generate a sort key for natural sort order."""
        # Split the string into chunks of digits and non-digits
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
    
    def process_directory(self):
        """Load images and tags from the selected directory."""
        if not self.directory:
            messagebox.showerror("Error", "Please select a directory first.")
            return

        # Reset data
        self.images = []
        self.image_tags = {}
        self.all_tags = set()
        self.current_image_index = -1

        # Scan directory
        for file in os.listdir(self.directory):
            if file.endswith(".png"):
                self.images.append(file)

        # Sort images in natural order
        self.images.sort(key=self.natural_sort_key)

        for image_name in self.images:
            tag_file = os.path.splitext(image_name)[0] + ".txt"
            tag_path = os.path.join(self.directory, tag_file)

            if os.path.exists(tag_path):
                with open(tag_path, "r") as f:
                    # Split by commas and strip whitespace
                    tags = [tag.strip() for tag in f.read().strip().split(",")]
                    self.image_tags[image_name] = tags
                    self.all_tags.update(tags)
            else:
                self.image_tags[image_name] = []

        self.update_ui()
    
    def update_ui(self):
        """Update the UI with loaded data."""
        # Update thumbnails
        self.display_thumbnails()

        # Preserve selection in All Tags
        selected_tags = self.all_tags_list.curselection()
        self.all_tags_list.delete(0, tk.END)
        for tag in sorted(self.all_tags, key=self.natural_sort_key):
            self.all_tags_list.insert(tk.END, tag)

        # Restore selection in All Tags
        for index in selected_tags:
            if index < self.all_tags_list.size():
                self.all_tags_list.selection_set(index)

        # Refresh the image tags if an image is selected
        if self.current_image_index != -1:
            self.select_image_by_index(self.current_image_index)


    
    def select_image(self, event=None):
        """Update the display to show the selected image and its tags."""
        selection = self.images_list.curselection()
        if not selection:
            return

        self.current_image_index = selection[0]
        image_name = self.images[self.current_image_index]

        # Update image display
        img_path = os.path.join(self.directory, image_name)
        self.display_selected_image(img_path)

        # Update tags list
        self.image_tags_list.delete(0, tk.END)
        for tag in self.image_tags[image_name]:
            self.image_tags_list.insert(tk.END, tag)

            
    def display_selected_image(self, image_path):
        """Display the selected image in the center with scaling."""
        img = Image.open(image_path)
        width, height = img.size

        # Get available space
        frame_width = self.image_display.winfo_width()
        frame_height = self.image_display.winfo_height()

        # Calculate scaling
        scale = min(frame_width / width, frame_height / height, 1)  # Do not upscale
        new_width = int(width * scale)
        new_height = int(height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)  # Use LANCZOS for resizing

        img_tk = ImageTk.PhotoImage(img)
        self.image_display.config(image=img_tk)
        self.image_display.image = img_tk  # Keep reference to avoid garbage collection


    def add_tag_to_current_image(self, event):
        """Add a tag from the all tags list to the current image."""
        if self.current_image_index == -1:
            return

        selection = self.all_tags_list.curselection()
        if not selection:
            return

        tag = self.all_tags_list.get(selection[0])
        image_name = self.images[self.current_image_index]

        if tag not in self.image_tags[image_name]:
            self.image_tags[image_name].append(tag)
            self.image_tags_list.insert(tk.END, tag)  # Directly update the image tags list
            self.update_all_tags_highlight()
            self.queue_file_save(image_name)  # Queue for saving

    
    def remove_tag_from_image(self, event):
        """Remove a tag from the current image."""
        if self.current_image_index == -1:
            return

        selection = self.image_tags_list.curselection()
        if not selection:
            return

        tag = self.image_tags_list.get(selection[0])
        image_name = self.images[self.current_image_index]

        if tag in self.image_tags[image_name]:
            self.image_tags[image_name].remove(tag)
            self.image_tags_list.delete(selection[0])  # Directly update the listbox
            self.update_all_tags_highlight()
            self.queue_file_save(image_name)  # Queue for saving

    def queue_file_save(self, image_name):
        """Queue an image's tags for saving in the background."""
        tags = self.image_tags[image_name]
        print(f"Queuing save for: {image_name} with tags: {tags}")  # Debugging log
        self.save_queue.put((image_name, tags))

    def update_all_tags_highlight(self):
        """Highlight tags in the All Tags list that are part of the current image's tags."""
        if self.current_image_index == -1:
            return

        # Get the default system colors
        default_bg = self.root.cget("bg")
        default_fg = self.all_tags_list.cget("fg")

        # Get the tags for the current image
        image_name = self.images[self.current_image_index]
        current_image_tags = set(self.image_tags[image_name])

        # Reset and update background colors in the All Tags list
        for index, tag in enumerate(self.all_tags_list.get(0, tk.END)):
            if tag in current_image_tags:
                self.all_tags_list.itemconfig(index, bg="lightgreen", fg=default_fg)
            else:
                self.all_tags_list.itemconfig(index, bg=default_bg, fg=default_fg)




    def on_close(self):
        """Handle application close."""
        print("Closing application...")

        # Signal the save thread to exit
        self.save_queue.put((None, None))

        # Wait for the queue to finish processing
        self.save_queue.join()

        # Wait for the thread to terminate
        self.save_thread.join()

        print("Application closed.")
        self.root.destroy()
        
    def highlight_tag_in_image_tags(self, tag):
        """Highlight a tag in the Image Tags list if it exists."""
        for index, current_tag in enumerate(self.image_tags_list.get(0, tk.END)):
            if current_tag == tag:
                self.image_tags_list.selection_clear(0, tk.END)  # Clear previous selections
                self.image_tags_list.selection_set(index)  # Highlight the matching tag
                self.image_tags_list.see(index)  # Scroll to make the tag visible
                break

            
    def find_tag_in_image_tags(self, event):
        """Select and scroll to a tag in Image Tags if it exists."""
        if self.current_image_index == -1:
            return

        # Get the selected tag from All Tags
        selection = self.all_tags_list.curselection()
        if not selection:
            return

        tag = self.all_tags_list.get(selection[0])

        # Check if the tag is in Image Tags
        image_name = self.images[self.current_image_index]
        if tag in self.image_tags[image_name]:
            # Highlight and scroll to the tag in Image Tags
            self.highlight_tag_in_image_tags(tag)


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageTaggerApp(root)
    root.mainloop()